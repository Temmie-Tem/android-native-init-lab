#include "a90_server_distro.h"

#include "a90_benchmark.h"
#include "a90_config.h"
#include "a90_console.h"
#include "a90_draw.h"
#include "a90_helper.h"
#include "a90_kms.h"
#include "a90_log.h"
#include "a90_run.h"
#include "a90_service.h"
#include "a90_util.h"

#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <limits.h>
#include <linux/loop.h>
#include <poll.h>
#include <stdbool.h>
#include <stdint.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <sys/statvfs.h>
#include <sys/sysmacros.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#ifndef O_CLOEXEC
#define O_CLOEXEC 0
#endif

#ifndef O_NOFOLLOW
#define O_NOFOLLOW 0
#endif

#define A90_D3_TAG "A90D3B"
#define A90_D3_TOKEN "SERVER-DISTRO-D3B-SWITCHROOT"
#define A90_D3_ALLOWED_IMAGE_ROOT "/mnt/sdext/a90/runtime/"
#define A90_D3_ROOT "/mnt/sdext/a90/runtime/distro-root"
#define A90_D3_WORK_IMAGE "/mnt/sdext/a90/runtime/d3-handoff-work.img"
#define A90_D3_LOOP "/dev/loop0"
#define A90_D3_BUSYBOX "/bin/busybox"
#define A90_D3_INIT "/sbin/init"
#define A90_D3_SWITCH_TIMEOUT_MS 30000
#define A90_D3_COPY_TIMEOUT_MS 300000
#define A90_D3_IMMUTABLE_TAG "A90D3H0"
#define A90_D3_SOURCE_RECEIPT_SCHEMA "a90-d3-source-receipt-v1"
#define A90_D3_SOURCE_RECEIPT_MAX 2048U
#define A90_D3_SOURCE_RECEIPT_CACHE_ROOT "/cache/"

/*
 * The writable set that replaces the full work copy.
 *
 * The copy existed to give Debian a writable root while the source stayed
 * pristine, and native-init deleted it on return -- so every Debian write was
 * already discarded each boot. Mounting the source read-only and covering the
 * few paths Debian actually writes keeps that behaviour exactly and stops
 * writing 2 GiB to the SD card on every handoff.
 *
 * The set is fixed and audited against the built rootfs rather than general:
 * /var/run and /var/lock are symlinks into /run, so /run covers them; the
 * network service generates its Dropbear host key under /etc/dropbear on every
 * boot; /tmp and /var/log are the remaining real directories Debian writes.
 */
#define A90_D3_WRITABLE_SET_MAX 4U

struct a90_d3_writable_entry {
    const char *path;
    const char *options;
};

/*
 * /tmp keeps the image's 01777 sticky semantics. Mounting it 0755 would leave
 * every non-root process unable to write there, which is a behaviour change
 * the work copy never made.
 */
static const struct a90_d3_writable_entry
a90_d3_writable_set[A90_D3_WRITABLE_SET_MAX] = {
    {"/run", "mode=0755"},
    {"/tmp", "mode=1777"},
    {"/etc/dropbear", "mode=0755"},
    {"/var/log", "mode=0755"},
};

/*
 * Debian cannot see the native namespace after switch_root: only /proc, /sys
 * and /dev are moved into the new root. So the durable evidence directory is
 * bind-mounted onto the image's empty /mnt before the switch, and Debian
 * addresses it as /mnt while native addresses the same bytes as
 * A90_D3_EVIDENCE_DIR. Only this directory crosses over -- never the SD as a
 * whole and never the source image, which stays reachable only through the
 * read-only loop.
 */
#define A90_D3_EVIDENCE_DIR "/mnt/sdext/a90/runtime/evidence"
#define A90_D3_EVIDENCE_LEAF "mnt"
#define A90_D3_WIFI_HANDOFF_DIR "/cache/a90-wifi-handoff"
#define A90_D3_WIFI_HANDOFF_LEAF "run/a90-native-wifi"
#define A90_D3_DISPLAY_RELEASE_TAG "A90D3DISPLAY"
#define A90_D3_DISPLAY_RELEASE_MARKER "run/a90-native-display-release"
#define A90_D_HANDOFF_HUD_TIMEOUT_MS 3000
#define A90_D_HANDOFF_DRM_OWNER_TIMEOUT_MS 1000
#define A90_D_HANDOFF_DRM_OWNER_MAX 16U
#define A90_D_HANDOFF_PROC_ENTRY_MAX 8192U
#define A90_D_HANDOFF_DISPLAY_TOTAL_TIMEOUT_MS 127000
#define A90_D_HW_TAG "A90DHW"
#define A90_DPUBLIC_HUD_TAG "A90WSTA136"
#define A90_DPUBLIC_HUD_SERVICE_TAG "A90WSTA140"
#define A90_DPUBLIC_HUD_SERVICE_DEDUP_TAG "A90WSTA142"
#define A90_DPUBLIC_HUD_SERVICE_DEDUP_MODE "same-content-consumed-or-rejected"
#define A90_DPUBLIC_HUD_SERVICE_SHARED_TAG "A90WSTA144"
#define A90_DPUBLIC_HUD_SERVICE_SHARED_MODE "shared-run-dir-bind-before-switch-root"
#define A90_DPUBLIC_HUD_SERVICE_RESTART_TAG "A90WSTA146"
#define A90_DPUBLIC_HUD_SERVICE_RESTART_MODE "restart-stop-start-stale-pid-cleanup"
#define A90_DPUBLIC_HUD_RUN_DIR "/run/a90-dpublic"
#define A90_DPUBLIC_HUD_RUN_SOURCE "a90-dpublic-hud"
#define A90_DPUBLIC_HUD_GROUP_GID 3904
#define A90_DPUBLIC_HUD_RUN_DIR_MODE 01770
#define A90_DPUBLIC_HUD_DEFAULT_INTENT A90_DPUBLIC_HUD_RUN_DIR "/hud-intent.json"
#define A90_DPUBLIC_HUD_SERVICE_PID A90_DPUBLIC_HUD_RUN_DIR "/hud-presenter.pid"
#define A90_DPUBLIC_HUD_SERVICE_STATUS A90_DPUBLIC_HUD_RUN_DIR "/hud-presenter.status"
#define A90_DPUBLIC_HUD_SERVICE_LOG A90_DPUBLIC_HUD_RUN_DIR "/hud-presenter.log"
#define A90_DPUBLIC_HUD_SCHEMA "a90-dpublic-hud-intent-v1"
#define A90_DPUBLIC_HUD_MAX_INTENT_BYTES 4096U
#define A90_DPUBLIC_HUD_STALE_AFTER_MS 2000ULL
#define A90_DPUBLIC_HUD_TITLE_MAX 32U
#define A90_DPUBLIC_HUD_STATE_MAX 24U
#define A90_DPUBLIC_HUD_MAX_LINES 6U
#define A90_DPUBLIC_HUD_LINE_MAX 48U
#define A90_DPUBLIC_HUD_SERVICE_POLL_MS 100
#define A90_DPUBLIC_HUD_SERVICE_STOP_TIMEOUT_MS 1000
#define A90_H17_TAG "A90H17"
#define A90_H17_OBSERVER_AUTH_SOURCE "/a90/h17/authorized_keys"
#define A90_H17_FIRSTBOOT_SOURCE "/a90/h17/firstboot"
#define A90_H17_AUTH_MAX_BYTES 512U

static int d3_path_is_mounted(const char *mountpoint);
static int d4_bind_dpublic_hud_run_dir(bool *bound_out);
static int d4_unbind_dpublic_hud_run_dir(void);

struct d3_display_release_proof {
    bool valid;
    unsigned int native_pid1_drm_fd_count;
    unsigned int other_drm_fd_count;
    bool native_kms_initialized;
    bool display_services_restart_blocked;
    struct a90_kms_release_result kms_release;
};

static struct d3_display_release_proof d3_last_display_release;

static void d_hw_print_contract(void) {
    a90_console_printf("A90DHW contract.version=1\r\n");
    a90_console_printf("A90DHW contract.document=docs/plans/SERVER_DISTRO_STAGE0_HARDWARE_CONTRACT_2026-07-04.md\r\n");
    a90_console_printf("A90DHW default.active=boot-control,usb-acm-ncm,storage-rootfs-handoff,drm-kms-boot-hud-release,health-status\r\n");
    a90_console_printf("A90DHW default.boot_control=active owner=native-until-switch_root\r\n");
    a90_console_printf("A90DHW default.usb_acm_ncm=active owner=kernel-gadget recovery=preserve\r\n");
    a90_console_printf("A90DHW default.storage_rootfs=active owner=native-validate-mount-before-switch_root debian_owns_after=1\r\n");
    a90_console_printf("A90DHW default.drm_kms=optional-boot-hud release_rule=stop-autohud-and-native-init-drm-owners-before-switch_root\r\n");
    a90_console_printf("A90DHW default.health_status=active owner=native-before-handoff\r\n");
    a90_console_printf("A90DHW next.required=wifi-sta-upstream\r\n");
    a90_console_printf("A90DHW next.wifi_sta=native-wlan0-materialization,debian-ip-route-tunnel\r\n");
    a90_console_printf("A90DHW optin=audio-adsp-acdb,kgsl-gpu,video-doom,touch-game-input,stress-longsoak\r\n");
    a90_console_printf("A90DHW denied.default_off=modem-cellular,camera,gnss,nfc,bluetooth,sensor-hubs,android-hal-services\r\n");
    a90_console_printf("A90DHW public_tunnel.owner=debian native=off inbound_public_ports=0\r\n");
    a90_console_printf("A90DHW safety.no=forbidden-partitions,raw-nonboot-flash,pmic-regulator-gdsc-gpio-backlight,panel-reinit\r\n");
    a90_console_printf("A90DHW end=1\r\n");
}

struct dpublic_hud_intent {
    uint64_t sequence;
    uint64_t monotonic_ms;
    char title[A90_DPUBLIC_HUD_TITLE_MAX + 1U];
    char public_state[A90_DPUBLIC_HUD_STATE_MAX + 1U];
    char upstream_state[A90_DPUBLIC_HUD_STATE_MAX + 1U];
    char service_state[A90_DPUBLIC_HUD_STATE_MAX + 1U];
    char packet_filter_state[A90_DPUBLIC_HUD_STATE_MAX + 1U];
    char lines[A90_DPUBLIC_HUD_MAX_LINES][A90_DPUBLIC_HUD_LINE_MAX + 1U];
    size_t line_count;
    size_t bytes;
    uint64_t age_ms;
};

struct dpublic_json_cursor {
    const char *p;
    const char *end;
};

static const char *const dpublic_hud_allowed_keys[] = {
    "schema",
    "sequence",
    "monotonic_ms",
    "title",
    "public_state",
    "upstream_state",
    "service_state",
    "packet_filter_state",
    "cpu_millic",
    "battery_percent",
    "lines",
};

static const char *const dpublic_hud_forbidden_keys[] = {
    "command",
    "argv",
    "path",
    "shell",
    "url",
    "ssid",
    "psk",
    "token",
    "secret",
};

static uint64_t dpublic_hud_monotonic_ms(void) {
    struct timespec ts;

    if (clock_gettime(CLOCK_MONOTONIC, &ts) < 0) {
        return 0;
    }
    return (uint64_t)ts.tv_sec * 1000ULL + (uint64_t)ts.tv_nsec / 1000000ULL;
}

static void dpublic_json_skip_ws(struct dpublic_json_cursor *cur) {
    while (cur->p < cur->end &&
           (*cur->p == ' ' || *cur->p == '\n' ||
            *cur->p == '\r' || *cur->p == '\t')) {
        cur->p++;
    }
}

static bool dpublic_hud_key_in_table(const char *key,
                                     const char *const *table,
                                     size_t count) {
    size_t i;

    for (i = 0; i < count; ++i) {
        if (strcmp(key, table[i]) == 0) {
            return true;
        }
    }
    return false;
}

static bool dpublic_hud_key_allowed(const char *key) {
    return dpublic_hud_key_in_table(key,
                                    dpublic_hud_allowed_keys,
                                    sizeof(dpublic_hud_allowed_keys) /
                                        sizeof(dpublic_hud_allowed_keys[0]));
}

static bool dpublic_hud_key_forbidden(const char *key) {
    return dpublic_hud_key_in_table(key,
                                    dpublic_hud_forbidden_keys,
                                    sizeof(dpublic_hud_forbidden_keys) /
                                        sizeof(dpublic_hud_forbidden_keys[0]));
}

static int dpublic_json_read_string(struct dpublic_json_cursor *cur,
                                    char *out,
                                    size_t out_size) {
    size_t used = 0;

    dpublic_json_skip_ws(cur);
    if (cur->p >= cur->end || *cur->p != '"' || out_size == 0) {
        return -EINVAL;
    }
    cur->p++;
    while (cur->p < cur->end) {
        unsigned char ch = (unsigned char)*cur->p++;

        if (ch == '"') {
            out[used] = '\0';
            return 0;
        }
        if (ch == '\\' || ch < 0x20 || ch > 0x7e) {
            return -EINVAL;
        }
        if (used + 1U >= out_size) {
            return -E2BIG;
        }
        out[used++] = (char)ch;
    }
    return -EINVAL;
}

static int dpublic_json_read_u64(struct dpublic_json_cursor *cur, uint64_t *out) {
    uint64_t value = 0;
    bool any = false;

    dpublic_json_skip_ws(cur);
    while (cur->p < cur->end && *cur->p >= '0' && *cur->p <= '9') {
        uint64_t digit = (uint64_t)(*cur->p - '0');

        if (value > (UINT64_MAX - digit) / 10ULL) {
            return -ERANGE;
        }
        value = value * 10ULL + digit;
        any = true;
        cur->p++;
    }
    if (!any) {
        return -EINVAL;
    }
    *out = value;
    return 0;
}

static int dpublic_json_skip_string(struct dpublic_json_cursor *cur) {
    char tmp[2];

    return dpublic_json_read_string(cur, tmp, sizeof(tmp));
}

static int dpublic_json_skip_balanced(struct dpublic_json_cursor *cur,
                                      char open_ch,
                                      char close_ch) {
    unsigned int depth = 0;
    bool in_string = false;

    dpublic_json_skip_ws(cur);
    if (cur->p >= cur->end || *cur->p != open_ch) {
        return -EINVAL;
    }
    while (cur->p < cur->end) {
        char ch = *cur->p++;

        if (in_string) {
            if (ch == '\\') {
                return -EINVAL;
            }
            if ((unsigned char)ch < 0x20) {
                return -EINVAL;
            }
            if (ch == '"') {
                in_string = false;
            }
            continue;
        }
        if (ch == '"') {
            in_string = true;
        } else if (ch == open_ch) {
            depth++;
        } else if (ch == close_ch) {
            if (depth == 0) {
                return -EINVAL;
            }
            depth--;
            if (depth == 0) {
                return 0;
            }
        }
    }
    return -EINVAL;
}

static int dpublic_json_skip_scalar(struct dpublic_json_cursor *cur) {
    dpublic_json_skip_ws(cur);
    while (cur->p < cur->end && *cur->p != ',' && *cur->p != '}') {
        if (*cur->p == '"' || *cur->p == '[' || *cur->p == '{') {
            return -EINVAL;
        }
        cur->p++;
    }
    return 0;
}

static int dpublic_json_skip_value(struct dpublic_json_cursor *cur) {
    dpublic_json_skip_ws(cur);
    if (cur->p >= cur->end) {
        return -EINVAL;
    }
    if (*cur->p == '"') {
        return dpublic_json_skip_string(cur);
    }
    if (*cur->p == '[') {
        return dpublic_json_skip_balanced(cur, '[', ']');
    }
    if (*cur->p == '{') {
        return dpublic_json_skip_balanced(cur, '{', '}');
    }
    return dpublic_json_skip_scalar(cur);
}

static int dpublic_json_read_lines(struct dpublic_json_cursor *cur,
                                   struct dpublic_hud_intent *intent) {
    dpublic_json_skip_ws(cur);
    if (cur->p >= cur->end || *cur->p != '[') {
        return -EINVAL;
    }
    cur->p++;
    dpublic_json_skip_ws(cur);
    if (cur->p < cur->end && *cur->p == ']') {
        cur->p++;
        return 0;
    }
    while (cur->p < cur->end) {
        if (intent->line_count >= A90_DPUBLIC_HUD_MAX_LINES) {
            return -E2BIG;
        }
        if (dpublic_json_read_string(cur,
                                     intent->lines[intent->line_count],
                                     sizeof(intent->lines[intent->line_count])) < 0) {
            return -EINVAL;
        }
        intent->line_count++;
        dpublic_json_skip_ws(cur);
        if (cur->p >= cur->end) {
            return -EINVAL;
        }
        if (*cur->p == ']') {
            cur->p++;
            return 0;
        }
        if (*cur->p != ',') {
            return -EINVAL;
        }
        cur->p++;
    }
    return -EINVAL;
}

static int dpublic_hud_parse_intent(const char *json,
                                    size_t used,
                                    struct dpublic_hud_intent *intent) {
    struct dpublic_json_cursor cur;
    char schema[64] = "";
    bool schema_seen = false;
    bool sequence_seen = false;
    bool monotonic_seen = false;
    uint64_t now_ms;

    memset(intent, 0, sizeof(*intent));
    snprintf(intent->title, sizeof(intent->title), "A90 SERVER");
    snprintf(intent->public_state, sizeof(intent->public_state), "UNKNOWN");
    snprintf(intent->upstream_state, sizeof(intent->upstream_state), "UNKNOWN");
    snprintf(intent->service_state, sizeof(intent->service_state), "UNKNOWN");
    snprintf(intent->packet_filter_state, sizeof(intent->packet_filter_state), "UNKNOWN");
    intent->bytes = used;

    cur.p = json;
    cur.end = json + used;
    dpublic_json_skip_ws(&cur);
    if (cur.p >= cur.end || *cur.p != '{') {
        return -EINVAL;
    }
    cur.p++;

    dpublic_json_skip_ws(&cur);
    while (cur.p < cur.end && *cur.p != '}') {
        char key[64];
        int rc;

        rc = dpublic_json_read_string(&cur, key, sizeof(key));
        if (rc < 0) {
            return rc;
        }
        if (dpublic_hud_key_forbidden(key)) {
            a90_console_printf("%s intent.reject=forbidden-key key=%s\r\n",
                               A90_DPUBLIC_HUD_TAG, key);
            return -EPERM;
        }
        if (!dpublic_hud_key_allowed(key)) {
            a90_console_printf("%s intent.reject=unknown-key key=%s\r\n",
                               A90_DPUBLIC_HUD_TAG, key);
            return -EPERM;
        }
        dpublic_json_skip_ws(&cur);
        if (cur.p >= cur.end || *cur.p != ':') {
            return -EINVAL;
        }
        cur.p++;

        if (strcmp(key, "schema") == 0) {
            rc = dpublic_json_read_string(&cur, schema, sizeof(schema));
            schema_seen = rc == 0;
        } else if (strcmp(key, "sequence") == 0) {
            rc = dpublic_json_read_u64(&cur, &intent->sequence);
            sequence_seen = rc == 0;
        } else if (strcmp(key, "monotonic_ms") == 0) {
            rc = dpublic_json_read_u64(&cur, &intent->monotonic_ms);
            monotonic_seen = rc == 0;
        } else if (strcmp(key, "title") == 0) {
            rc = dpublic_json_read_string(&cur, intent->title, sizeof(intent->title));
        } else if (strcmp(key, "public_state") == 0) {
            rc = dpublic_json_read_string(&cur, intent->public_state, sizeof(intent->public_state));
        } else if (strcmp(key, "upstream_state") == 0) {
            rc = dpublic_json_read_string(&cur, intent->upstream_state, sizeof(intent->upstream_state));
        } else if (strcmp(key, "service_state") == 0) {
            rc = dpublic_json_read_string(&cur, intent->service_state, sizeof(intent->service_state));
        } else if (strcmp(key, "packet_filter_state") == 0) {
            rc = dpublic_json_read_string(&cur,
                                          intent->packet_filter_state,
                                          sizeof(intent->packet_filter_state));
        } else if (strcmp(key, "lines") == 0) {
            rc = dpublic_json_read_lines(&cur, intent);
        } else {
            rc = dpublic_json_skip_value(&cur);
        }
        if (rc < 0) {
            return rc;
        }

        dpublic_json_skip_ws(&cur);
        if (cur.p >= cur.end) {
            return -EINVAL;
        }
        if (*cur.p == ',') {
            cur.p++;
            dpublic_json_skip_ws(&cur);
            continue;
        }
        if (*cur.p != '}') {
            return -EINVAL;
        }
    }
    if (cur.p >= cur.end || *cur.p != '}') {
        return -EINVAL;
    }
    cur.p++;
    dpublic_json_skip_ws(&cur);
    if (cur.p != cur.end) {
        return -EINVAL;
    }
    if (!schema_seen || strcmp(schema, A90_DPUBLIC_HUD_SCHEMA) != 0 ||
        !sequence_seen || !monotonic_seen || intent->sequence == 0) {
        return -EINVAL;
    }

    now_ms = dpublic_hud_monotonic_ms();
    if (now_ms == 0 || intent->monotonic_ms > now_ms) {
        a90_console_printf("%s intent.reject=clock-domain now_ms=%llu intent_ms=%llu\r\n",
                           A90_DPUBLIC_HUD_TAG,
                           (unsigned long long)now_ms,
                           (unsigned long long)intent->monotonic_ms);
        return -ESTALE;
    }
    intent->age_ms = now_ms - intent->monotonic_ms;
    if (intent->age_ms > A90_DPUBLIC_HUD_STALE_AFTER_MS) {
        a90_console_printf("%s intent.reject=stale age_ms=%llu stale_after_ms=%llu\r\n",
                           A90_DPUBLIC_HUD_TAG,
                           (unsigned long long)intent->age_ms,
                           (unsigned long long)A90_DPUBLIC_HUD_STALE_AFTER_MS);
        return -ETIMEDOUT;
    }
    return 0;
}

static int dpublic_hud_read_intent_file(const char *path,
                                        char *json,
                                        size_t json_size,
                                        size_t *used_out) {
    struct stat st;
    ssize_t nread;
    int fd;

    if (json_size <= A90_DPUBLIC_HUD_MAX_INTENT_BYTES) {
        return -EINVAL;
    }
    fd = open(path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) {
        return -errno;
    }
    if (fstat(fd, &st) < 0) {
        int saved = errno;
        close(fd);
        return -saved;
    }
    if (!S_ISREG(st.st_mode) ||
        st.st_size <= 0 ||
        st.st_size > (off_t)A90_DPUBLIC_HUD_MAX_INTENT_BYTES) {
        close(fd);
        return -E2BIG;
    }
    nread = read(fd, json, A90_DPUBLIC_HUD_MAX_INTENT_BYTES + 1U);
    close(fd);
    if (nread <= 0 || nread > (ssize_t)A90_DPUBLIC_HUD_MAX_INTENT_BYTES) {
        return -E2BIG;
    }
    json[nread] = '\0';
    *used_out = (size_t)nread;
    return 0;
}

static void dpublic_hud_draw_presenter(const struct dpublic_hud_intent *intent) {
    struct a90_fb *fb = a90_kms_framebuffer();
    uint32_t margin;
    uint32_t width;
    uint32_t y;
    uint32_t scale;
    uint32_t line_h;
    char line[160];
    size_t i;

    if (fb == NULL) {
        return;
    }
    scale = fb->width >= 1000U ? 5U : 3U;
    margin = fb->width / 18U;
    width = fb->width > margin * 2U ? fb->width - margin * 2U : fb->width;
    y = fb->height / 10U;
    line_h = scale * 12U;

    a90_draw_text_fit(fb, margin, y, intent->title, 0xffffff, scale + 1U, width);
    y += line_h + scale * 5U;
    snprintf(line, sizeof(line), "PUBLIC %s", intent->public_state);
    a90_draw_text_fit(fb, margin, y, line, 0x80ff80, scale, width);
    y += line_h;
    snprintf(line, sizeof(line), "UPSTREAM %s   SERVICE %s",
             intent->upstream_state, intent->service_state);
    a90_draw_text_fit(fb, margin, y, line, 0xdce6f0, scale, width);
    y += line_h;
    snprintf(line, sizeof(line), "PACKET FILTER %s", intent->packet_filter_state);
    a90_draw_text_fit(fb, margin, y, line, 0xdce6f0, scale, width);
    y += line_h + scale * 5U;
    a90_draw_text_fit(fb,
                      margin,
                      y,
                      "NATIVE ROOT PRESENTER OWNS KMS",
                      0xffcc33,
                      scale,
                      width);
    y += line_h;
    snprintf(line,
             sizeof(line),
             "SEQ %llu  AGE %llums",
             (unsigned long long)intent->sequence,
             (unsigned long long)intent->age_ms);
    a90_draw_text_fit(fb, margin, y, line, 0x9ca8b5, scale > 1U ? scale - 1U : 1U, width);
    y += line_h + scale * 4U;

    for (i = 0; i < intent->line_count; ++i) {
        a90_draw_text_fit(fb,
                          margin + scale * 4U,
                          y,
                          intent->lines[i],
                          0xdce6f0,
                          scale > 1U ? scale - 1U : 1U,
                          width - scale * 4U);
        y += line_h;
    }
}

static int dpublic_hud_present_bootstrap(void) {
    struct dpublic_hud_intent intent;
    int rc;

    memset(&intent, 0, sizeof(intent));
    intent.sequence = 1;
    snprintf(intent.title, sizeof(intent.title), "A90 SERVER");
    snprintf(intent.public_state, sizeof(intent.public_state), "PRIVATE");
    snprintf(intent.upstream_state, sizeof(intent.upstream_state), "STARTING");
    snprintf(intent.service_state, sizeof(intent.service_state), "DEBIAN BOOT");
    snprintf(intent.packet_filter_state,
             sizeof(intent.packet_filter_state),
             "LOCKED");
    snprintf(intent.lines[intent.line_count++],
             sizeof(intent.lines[0]),
             "UFS ROOT READ-ONLY");
    snprintf(intent.lines[intent.line_count++],
             sizeof(intent.lines[0]),
             "SSH AUTH OVERLAY READY");
    snprintf(intent.lines[intent.line_count++],
             sizeof(intent.lines[0]),
             "SWITCHING TO DEBIAN");
    rc = a90_kms_begin_frame(0x061018);
    if (rc < 0) {
        return rc;
    }
    dpublic_hud_draw_presenter(&intent);
    return a90_kms_present("h17-persistent-hud-bootstrap", true);
}

int a90_server_distro_dpublic_hud_presenter_cmd(char **argv, int argc) {
    const char *mode = "present";
    const char *path = A90_DPUBLIC_HUD_DEFAULT_INTENT;
    struct dpublic_hud_intent intent;
    char json[A90_DPUBLIC_HUD_MAX_INTENT_BYTES + 1U];
    size_t used = 0;
    bool validate_only = false;
    int rc;

    if (argc == 2) {
        if (strcmp(argv[1], "validate") == 0 || strcmp(argv[1], "present") == 0) {
            mode = argv[1];
        } else {
            path = argv[1];
        }
    } else if (argc == 3) {
        mode = argv[1];
        path = argv[2];
    } else if (argc != 1) {
        a90_console_printf("usage: dpublic-hud-presenter [validate|present] [intent-path]\r\n");
        return -EINVAL;
    }
    if (strcmp(mode, "validate") == 0) {
        validate_only = true;
    } else if (strcmp(mode, "present") != 0) {
        a90_console_printf("usage: dpublic-hud-presenter [validate|present] [intent-path]\r\n");
        a90_console_printf("%s refused=unknown-mode mode=%s\r\n", A90_DPUBLIC_HUD_TAG, mode);
        return -EINVAL;
    }

    rc = dpublic_hud_read_intent_file(path, json, sizeof(json), &used);
    if (rc < 0) {
        a90_console_printf("%s intent.path=%s\r\n", A90_DPUBLIC_HUD_TAG, path);
        a90_console_printf("%s intent.read_rc=%d\r\n", A90_DPUBLIC_HUD_TAG, rc);
        return rc;
    }
    rc = dpublic_hud_parse_intent(json, used, &intent);
    if (rc < 0) {
        a90_console_printf("%s intent.path=%s\r\n", A90_DPUBLIC_HUD_TAG, path);
        a90_console_printf("%s intent.bytes=%zu\r\n", A90_DPUBLIC_HUD_TAG, used);
        a90_console_printf("%s intent.valid=0 rc=%d\r\n", A90_DPUBLIC_HUD_TAG, rc);
        return rc;
    }

    a90_console_printf("%s intent.path=%s\r\n", A90_DPUBLIC_HUD_TAG, path);
    a90_console_printf("%s intent.bytes=%zu\r\n", A90_DPUBLIC_HUD_TAG, intent.bytes);
    a90_console_printf("%s intent.valid=1\r\n", A90_DPUBLIC_HUD_TAG);
    a90_console_printf("%s intent.sequence=%llu\r\n",
                       A90_DPUBLIC_HUD_TAG,
                       (unsigned long long)intent.sequence);
    a90_console_printf("%s intent.age_ms=%llu\r\n",
                       A90_DPUBLIC_HUD_TAG,
                       (unsigned long long)intent.age_ms);
    a90_console_printf("%s policy.forbidden_fields=reject\r\n", A90_DPUBLIC_HUD_TAG);
    a90_console_printf("%s policy.unknown_fields=reject\r\n", A90_DPUBLIC_HUD_TAG);
    a90_console_printf("%s policy.stale_after_ms=%llu\r\n",
                       A90_DPUBLIC_HUD_TAG,
                       (unsigned long long)A90_DPUBLIC_HUD_STALE_AFTER_MS);
    a90_console_printf("%s presenter.owner=native-init-root\r\n", A90_DPUBLIC_HUD_TAG);
    a90_console_printf("%s presenter.debian_direct_kms=0\r\n", A90_DPUBLIC_HUD_TAG);
    if (validate_only) {
        a90_console_printf("%s present.skipped=validate-only\r\n", A90_DPUBLIC_HUD_TAG);
        return 0;
    }

    rc = a90_kms_begin_frame(0x061018);
    a90_console_printf("%s present.begin_frame_rc=%d\r\n", A90_DPUBLIC_HUD_TAG, rc);
    if (rc < 0) {
        return rc;
    }
    dpublic_hud_draw_presenter(&intent);
    rc = a90_kms_present("dpublic-hud-presenter", true);
    a90_console_printf("%s present.rc=%d\r\n", A90_DPUBLIC_HUD_TAG, rc);
    if (rc < 0) {
        return rc;
    }
    a90_console_printf("%s present.done=1\r\n", A90_DPUBLIC_HUD_TAG);
    return 0;
}

int a90_server_distro_cmd(char **argv, int argc) {
    const char *mode;

    if (argc == 1) {
        mode = "status";
    } else if (argc == 2) {
        mode = argv[1];
    } else {
        a90_console_printf("usage: server-distro [status|hardware-contract]\r\n");
        return -EINVAL;
    }

    if (strcmp(mode, "status") == 0 || strcmp(mode, "hardware-contract") == 0) {
        d_hw_print_contract();
        return 0;
    }

    a90_console_printf("usage: server-distro [status|hardware-contract]\r\n");
    a90_console_printf("%s refused=unknown-mode mode=%s\r\n", A90_D_HW_TAG, mode);
    return -EINVAL;
}

static int d_handoff_parse_pid(const char *name, pid_t *pid_out) {
    char *end = NULL;
    long value;

    if (name == NULL || name[0] == '\0' || pid_out == NULL) {
        return -EINVAL;
    }
    errno = 0;
    value = strtol(name, &end, 10);
    if (errno != 0 || end == name || end == NULL || *end != '\0' || value <= 0) {
        return -EINVAL;
    }
    *pid_out = (pid_t)value;
    return 0;
}

static int d_handoff_readlink(const char *path, char *out, size_t out_size) {
    ssize_t nread;

    if (path == NULL || out == NULL || out_size == 0) {
        return -EINVAL;
    }
    nread = readlink(path, out, out_size - 1);
    if (nread < 0) {
        return -errno;
    }
    out[nread] = '\0';
    return 0;
}

static bool d_handoff_path_is_drm_target(const char *target) {
    return target != NULL &&
           (strstr(target, "/dri/") != NULL ||
            strstr(target, "card0") != NULL ||
            strstr(target, "drm") != NULL);
}

static bool d_handoff_pid_is_native_init(pid_t pid) {
    char path[64];
    char target[PATH_MAX];

    if (pid <= 1 || pid == getpid()) {
        return false;
    }
    snprintf(path, sizeof(path), "/proc/%ld/exe", (long)pid);
    if (d_handoff_readlink(path, target, sizeof(target)) < 0) {
        return false;
    }
    return strcmp(target, "/init") == 0;
}

static bool d_handoff_deadline_expired(long deadline_ms) {
    return deadline_ms > 0 && monotonic_millis() >= deadline_ms;
}

static int d_handoff_deadline_remaining_ms(long deadline_ms, int cap_ms) {
    long remaining;

    if (cap_ms <= 0) {
        return 0;
    }
    if (deadline_ms <= 0) {
        return cap_ms;
    }
    remaining = deadline_ms - monotonic_millis();
    if (remaining <= 0) {
        return 0;
    }
    return remaining < cap_ms ? (int)remaining : cap_ms;
}

static int d_handoff_count_pid_drm_fds(pid_t pid,
                                       unsigned int *count_out,
                                       long deadline_ms) {
    char dir_path[64];
    DIR *dir;
    struct dirent *entry;
    unsigned int count = 0;

    if (pid <= 0 || count_out == NULL) {
        return -EINVAL;
    }
    *count_out = 0;
    if (d_handoff_deadline_expired(deadline_ms)) {
        return -ETIMEDOUT;
    }

    snprintf(dir_path, sizeof(dir_path), "/proc/%ld/fd", (long)pid);
    dir = opendir(dir_path);
    if (dir == NULL) {
        if (errno == ENOENT || errno == ESRCH) {
            return 0;
        }
        return -errno;
    }
    while ((entry = readdir(dir)) != NULL) {
        char fd_path[PATH_MAX];
        char target[PATH_MAX];
        int rc;

        if (d_handoff_deadline_expired(deadline_ms)) {
            closedir(dir);
            return -ETIMEDOUT;
        }
        if (entry->d_name[0] == '.') {
            continue;
        }
        snprintf(fd_path, sizeof(fd_path), "%s/%s", dir_path, entry->d_name);
        rc = d_handoff_readlink(fd_path, target, sizeof(target));
        if (rc < 0) {
            if (rc == -ENOENT || rc == -ESRCH) {
                continue;
            }
            closedir(dir);
            return rc;
        }
        if (d_handoff_path_is_drm_target(target)) {
            count++;
        }
    }
    if (d_handoff_deadline_expired(deadline_ms)) {
        closedir(dir);
        return -ETIMEDOUT;
    }
    closedir(dir);
    *count_out = count;
    return 0;
}

static bool d_handoff_pid_has_drm_fd(pid_t pid) {
    unsigned int count = 0;

    return d_handoff_count_pid_drm_fds(pid, &count, 0) == 0 && count != 0U;
}

static int d_handoff_pid_has_drm_fd_until(pid_t pid,
                                          long deadline_ms,
                                          bool *has_drm_out) {
    unsigned int count = 0;
    int rc;

    if (has_drm_out == NULL) {
        return -EINVAL;
    }
    rc = d_handoff_count_pid_drm_fds(pid, &count, deadline_ms);
    if (rc < 0) {
        return rc;
    }
    *has_drm_out = count != 0U;
    return 0;
}

static int d_handoff_count_all_drm_fds(pid_t native_pid1,
                                       unsigned int *native_pid1_count_out,
                                       unsigned int *other_count_out,
                                       long deadline_ms) {
    DIR *proc;
    struct dirent *entry;
    unsigned int native_pid1_count = 0;
    unsigned int other_count = 0;
    unsigned int process_entries = 0;

    if (native_pid1 <= 0 ||
        native_pid1_count_out == NULL ||
        other_count_out == NULL) {
        return -EINVAL;
    }
    proc = opendir("/proc");
    if (proc == NULL) {
        return -errno;
    }
    while ((entry = readdir(proc)) != NULL) {
        pid_t pid;
        unsigned int count = 0;
        int rc;

        if (d_handoff_deadline_expired(deadline_ms)) {
            closedir(proc);
            return -ETIMEDOUT;
        }
        if (d_handoff_parse_pid(entry->d_name, &pid) < 0) {
            continue;
        }
        if (++process_entries > A90_D_HANDOFF_PROC_ENTRY_MAX) {
            closedir(proc);
            return -E2BIG;
        }
        rc = d_handoff_count_pid_drm_fds(pid, &count, deadline_ms);
        if (rc < 0) {
            closedir(proc);
            return rc;
        }
        if (pid == native_pid1) {
            native_pid1_count += count;
        } else {
            other_count += count;
        }
    }
    closedir(proc);
    *native_pid1_count_out = native_pid1_count;
    *other_count_out = other_count;
    return 0;
}

static bool d_handoff_pid_alive(pid_t pid) {
    if (pid <= 0) {
        return false;
    }
    if (kill(pid, 0) == 0) {
        return true;
    }
    return errno == EPERM;
}

static int d_handoff_wait_pid_gone(pid_t pid, int timeout_ms) {
    long deadline = monotonic_millis() + timeout_ms;

    while (monotonic_millis() < deadline) {
        int status = 0;
        pid_t got = waitpid(pid, &status, WNOHANG);

        if (got == pid) {
            return 0;
        }
        if (!d_handoff_pid_alive(pid)) {
            return 0;
        }
        usleep(100000);
    }
    return d_handoff_pid_alive(pid) ? -EBUSY : 0;
}

static int d_handoff_stop_drm_owner_until(const char *tag,
                                          pid_t pid,
                                          long deadline_ms);
static int d_handoff_stop_drm_owner(const char *tag, pid_t pid);

struct dpublic_hud_service_opts {
    const char *intent_path;
    const char *pid_path;
    const char *status_path;
    bool release_drm;
    bool preopen_drm;
};

static volatile sig_atomic_t dpublic_hud_service_stop_requested = 0;

static void dpublic_hud_service_signal(int signo) {
    (void)signo;
    dpublic_hud_service_stop_requested = 1;
}

static void dpublic_hud_service_default_opts(struct dpublic_hud_service_opts *opts) {
    opts->intent_path = A90_DPUBLIC_HUD_DEFAULT_INTENT;
    opts->pid_path = A90_DPUBLIC_HUD_SERVICE_PID;
    opts->status_path = A90_DPUBLIC_HUD_SERVICE_STATUS;
    opts->release_drm = false;
    opts->preopen_drm = false;
}

static int dpublic_hud_service_parse_opts(char **argv,
                                          int argc,
                                          int start_index,
                                          struct dpublic_hud_service_opts *opts) {
    int i;

    dpublic_hud_service_default_opts(opts);
    for (i = start_index; i < argc; ++i) {
        if (strcmp(argv[i], "--intent") == 0 && i + 1 < argc) {
            opts->intent_path = argv[++i];
        } else if (strcmp(argv[i], "--pid-file") == 0 && i + 1 < argc) {
            opts->pid_path = argv[++i];
        } else if (strcmp(argv[i], "--status-file") == 0 && i + 1 < argc) {
            opts->status_path = argv[++i];
        } else if (strcmp(argv[i], "--stale-after-ms") == 0 && i + 1 < argc) {
            char *end = NULL;
            long value;

            errno = 0;
            value = strtol(argv[++i], &end, 10);
            if (errno != 0 || end == argv[i] || end == NULL || *end != '\0' ||
                value != (long)A90_DPUBLIC_HUD_STALE_AFTER_MS) {
                return -EINVAL;
            }
        } else if (strcmp(argv[i], "--release-drm") == 0) {
            opts->release_drm = true;
        } else {
            return -EINVAL;
        }
    }
    return 0;
}

static int dpublic_hud_service_write_text(const char *path, const char *text) {
    int fd;
    size_t len;
    ssize_t written;

    if (path == NULL || text == NULL) {
        return -EINVAL;
    }
    fd = open(path, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC, 0644);
    if (fd < 0) {
        return -errno;
    }
    len = strlen(text);
    written = write(fd, text, len);
    if (written < 0 || (size_t)written != len) {
        int rc = written < 0 ? -errno : -EIO;

        close(fd);
        return rc;
    }
    if (close(fd) < 0) {
        return -errno;
    }
    return 0;
}

static bool dpublic_hud_mount_option_present(const char *options,
                                             const char *wanted) {
    size_t wanted_len;
    const char *cursor;

    if (options == NULL || wanted == NULL || wanted[0] == '\0') {
        return false;
    }
    wanted_len = strlen(wanted);
    cursor = options;
    while (*cursor != '\0') {
        const char *end = strchr(cursor, ',');
        size_t length = end == NULL ? strlen(cursor) : (size_t)(end - cursor);

        if (length == wanted_len && memcmp(cursor, wanted, wanted_len) == 0) {
            return true;
        }
        if (end == NULL) {
            break;
        }
        cursor = end + 1;
    }
    return false;
}

static int dpublic_hud_service_verify_shared_run_mount(const char *mountpoint) {
    FILE *fp;
    struct statvfs fs;
    char line[4096];
    unsigned int matches = 0;
    bool exact = false;
    int rc = 0;

    if (mountpoint == NULL || mountpoint[0] != '/') {
        return -EINVAL;
    }
    fp = fopen("/proc/mounts", "r");
    if (fp == NULL) {
        return -errno;
    }
    while (fgets(line, sizeof(line), fp) != NULL) {
        char source[PATH_MAX];
        char target[PATH_MAX];
        char fstype[64];
        char options[1024];

        if (strchr(line, '\n') == NULL && !feof(fp)) {
            rc = -EOVERFLOW;
            break;
        }
        if (sscanf(line,
                   "%1023s %1023s %63s %1023s %*d %*d",
                   source,
                   target,
                   fstype,
                   options) != 4 ||
            strcmp(target, mountpoint) != 0) {
            continue;
        }
        matches += 1U;
        exact = strcmp(source, A90_DPUBLIC_HUD_RUN_SOURCE) == 0 &&
                strcmp(fstype, "tmpfs") == 0 &&
                dpublic_hud_mount_option_present(options, "rw") &&
                dpublic_hud_mount_option_present(options, "nosuid") &&
                dpublic_hud_mount_option_present(options, "nodev") &&
                !dpublic_hud_mount_option_present(options, "ro");
    }
    if (ferror(fp) && rc == 0) {
        rc = -EIO;
    }
    if (fclose(fp) < 0 && rc == 0) {
        rc = -errno;
    }
    if (rc < 0) {
        return rc;
    }
    if (matches != 1U || !exact) {
        return -ESTALE;
    }
    if (statvfs(mountpoint, &fs) < 0) {
        return -errno;
    }
    if ((fs.f_flag & ST_NOSUID) == 0 ||
        (fs.f_flag & ST_RDONLY) != 0) {
        return -EPERM;
    }
    return 0;
}

static int dpublic_hud_service_mount_shared_run_dir(void) {
    int mounted;
    int rc;

    mounted = d3_path_is_mounted(A90_DPUBLIC_HUD_RUN_DIR);
    if (mounted < 0) {
        return mounted;
    }
    if (mounted) {
        rc = dpublic_hud_service_verify_shared_run_mount(
            A90_DPUBLIC_HUD_RUN_DIR);
        if (rc < 0) {
            a90_console_printf(
                "%s shared_run_dir=existing-invalid path=%s rc=%d\r\n",
                A90_DPUBLIC_HUD_SERVICE_SHARED_TAG,
                A90_DPUBLIC_HUD_RUN_DIR,
                rc);
            return rc;
        }
        a90_console_printf("%s shared_run_dir=already-mounted path=%s\r\n",
                           A90_DPUBLIC_HUD_SERVICE_SHARED_TAG,
                           A90_DPUBLIC_HUD_RUN_DIR);
        return 0;
    }
    if (mount(A90_DPUBLIC_HUD_RUN_SOURCE,
              A90_DPUBLIC_HUD_RUN_DIR,
              "tmpfs",
              MS_NOSUID | MS_NODEV,
              "mode=1770,uid=0,gid=3904,size=256k") < 0) {
        int rc = -errno;

        a90_console_printf("%s shared_run_dir=mount-fail path=%s rc=%d errno=%d (%s)\r\n",
                           A90_DPUBLIC_HUD_SERVICE_SHARED_TAG,
                           A90_DPUBLIC_HUD_RUN_DIR,
                           rc,
                           -rc,
                           strerror(-rc));
        return rc;
    }
    rc = dpublic_hud_service_verify_shared_run_mount(A90_DPUBLIC_HUD_RUN_DIR);
    if (rc < 0) {
        int cleanup_rc = 0;

        if (umount2(A90_DPUBLIC_HUD_RUN_DIR, MNT_DETACH) < 0) {
            cleanup_rc = -errno;
        }
        a90_console_printf(
            "%s shared_run_dir=verify-fail path=%s rc=%d cleanup_rc=%d\r\n",
            A90_DPUBLIC_HUD_SERVICE_SHARED_TAG,
            A90_DPUBLIC_HUD_RUN_DIR,
            rc,
            cleanup_rc);
        return cleanup_rc < 0 ? cleanup_rc : rc;
    }
    a90_console_printf("%s shared_run_dir=mounted path=%s fstype=tmpfs mode=1770 owner=root:a90hud\r\n",
                       A90_DPUBLIC_HUD_SERVICE_SHARED_TAG,
                       A90_DPUBLIC_HUD_RUN_DIR);
    return 0;
}

static int dpublic_hud_service_prepare_run_dir(void) {
    int rc = 0;

    if (mkdir("/run", 0755) < 0 && errno != EEXIST) {
        return -errno;
    }
    if (mkdir(A90_DPUBLIC_HUD_RUN_DIR, A90_DPUBLIC_HUD_RUN_DIR_MODE) < 0 &&
        errno != EEXIST) {
        return -errno;
    }
    rc = dpublic_hud_service_mount_shared_run_dir();
    if (rc < 0) {
        return rc;
    }
    if (chown(A90_DPUBLIC_HUD_RUN_DIR, 0, A90_DPUBLIC_HUD_GROUP_GID) < 0) {
        rc = -errno;
    }
    if (chmod(A90_DPUBLIC_HUD_RUN_DIR, A90_DPUBLIC_HUD_RUN_DIR_MODE) < 0 && rc == 0) {
        rc = -errno;
    }
    return rc;
}

static int dpublic_hud_service_write_pid(const char *path, pid_t pid) {
    char text[64];

    snprintf(text, sizeof(text), "%ld\n", (long)pid);
    return dpublic_hud_service_write_text(path, text);
}

static int dpublic_hud_service_read_pid(const char *path, pid_t *pid_out) {
    int fd;
    char buf[64];
    ssize_t nread;
    char *end = NULL;
    long value;

    if (path == NULL || pid_out == NULL) {
        return -EINVAL;
    }
    fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        return -errno;
    }
    nread = read(fd, buf, sizeof(buf) - 1);
    close(fd);
    if (nread <= 0) {
        return nread < 0 ? -errno : -EIO;
    }
    buf[nread] = '\0';
    errno = 0;
    value = strtol(buf, &end, 10);
    if (errno != 0 || end == buf || value <= 0) {
        return -EINVAL;
    }
    *pid_out = (pid_t)value;
    return 0;
}

static int dpublic_hud_service_write_status(const char *path,
                                            const char *state,
                                            pid_t pid,
                                            uint64_t sequence,
                                            int present_rc) {
    char text[512];

    snprintf(text,
             sizeof(text),
             "state=%s\npid=%ld\nlast_sequence=%llu\npresent_rc=%d\n"
             "intent=%s\nowner=native-init\nprocess_model=forked-native-child-survives-switch-root\n",
             state,
             (long)pid,
             (unsigned long long)sequence,
             present_rc,
             A90_DPUBLIC_HUD_DEFAULT_INTENT);
    return dpublic_hud_service_write_text(path, text);
}

static bool dpublic_hud_service_same_content(const char *left,
                                             size_t left_used,
                                             const char *right,
                                             size_t right_used) {
    return left_used == right_used && left_used > 0 && memcmp(left, right, left_used) == 0;
}

static int dpublic_hud_service_child_loop(const char *intent_path,
                                          const char *status_path,
                                          bool preopen_drm,
                                          int ready_fd) {
    uint64_t last_sequence = 0;
    int last_present_rc = 0;
    char consumed_json[A90_DPUBLIC_HUD_MAX_INTENT_BYTES + 1U];
    size_t consumed_used = 0;
    char rejected_json[A90_DPUBLIC_HUD_MAX_INTENT_BYTES + 1U];
    size_t rejected_used = 0;

    dpublic_hud_service_stop_requested = 0;
    signal(SIGTERM, dpublic_hud_service_signal);
    signal(SIGINT, dpublic_hud_service_signal);
    signal(SIGHUP, dpublic_hud_service_signal);
    if (preopen_drm) {
        int bootstrap_rc = dpublic_hud_present_bootstrap();

        if (ready_fd >= 0) {
            ssize_t ready_written =
                write(ready_fd, &bootstrap_rc, sizeof(bootstrap_rc));

            (void)close(ready_fd);
            if (ready_written != (ssize_t)sizeof(bootstrap_rc)) {
                return -EIO;
            }
        }
        if (bootstrap_rc < 0) {
            return bootstrap_rc;
        }
        last_present_rc = bootstrap_rc;
    } else if (ready_fd >= 0) {
        int ready_rc = 0;
        ssize_t ready_written = write(ready_fd, &ready_rc, sizeof(ready_rc));

        (void)close(ready_fd);
        if (ready_written != (ssize_t)sizeof(ready_rc)) {
            return -EIO;
        }
    }
    (void)dpublic_hud_service_write_status(
        status_path, "running", getpid(), 0, last_present_rc);

    while (!dpublic_hud_service_stop_requested) {
        struct dpublic_hud_intent intent;
        char json[A90_DPUBLIC_HUD_MAX_INTENT_BYTES + 1U];
        size_t used = 0;
        int rc = dpublic_hud_read_intent_file(intent_path, json, sizeof(json), &used);

        if (rc == 0) {
            if (dpublic_hud_service_same_content(json, used, consumed_json, consumed_used) ||
                dpublic_hud_service_same_content(json, used, rejected_json, rejected_used)) {
                usleep(A90_DPUBLIC_HUD_SERVICE_POLL_MS * 1000U);
                continue;
            }
            rc = dpublic_hud_parse_intent(json, used, &intent);
            if (rc == 0 && intent.sequence != last_sequence) {
                last_sequence = intent.sequence;
                last_present_rc = a90_kms_begin_frame(0x061018);
                if (last_present_rc == 0) {
                    dpublic_hud_draw_presenter(&intent);
                    last_present_rc = a90_kms_present("dpublic-hud-presenter-service", true);
                }
                memcpy(consumed_json, json, used);
                consumed_used = used;
                rejected_used = 0;
                (void)dpublic_hud_service_write_status(status_path,
                                                       "running",
                                                       getpid(),
                                                       last_sequence,
                                                       last_present_rc);
            } else if (rc == 0) {
                memcpy(consumed_json, json, used);
                consumed_used = used;
                rejected_used = 0;
            } else if (rc < 0) {
                memcpy(rejected_json, json, used);
                rejected_used = used;
            }
        }
        usleep(A90_DPUBLIC_HUD_SERVICE_POLL_MS * 1000U);
    }

    (void)dpublic_hud_service_write_status(status_path,
                                           "stopped",
                                           getpid(),
                                           last_sequence,
                                           last_present_rc);
    return 0;
}

static bool dpublic_hud_service_pid_is_default(pid_t pid) {
    pid_t service_pid;

    if (dpublic_hud_service_read_pid(A90_DPUBLIC_HUD_SERVICE_PID, &service_pid) < 0) {
        return false;
    }
    return service_pid == pid && d_handoff_pid_alive(pid);
}

static int dpublic_hud_service_start(const struct dpublic_hud_service_opts *opts,
                                     pid_t *child_pid_out) {
    pid_t existing;
    pid_t pid;
    int ready_pipe[2] = {-1, -1};
    int rc;

    if (child_pid_out != NULL) {
        *child_pid_out = -1;
    }
    rc = dpublic_hud_service_prepare_run_dir();
    a90_console_printf("%s start.run_dir=%s owner=root:a90hud mode=1770 rc=%d\r\n",
                       A90_DPUBLIC_HUD_SERVICE_TAG, A90_DPUBLIC_HUD_RUN_DIR, rc);
    if (rc < 0) {
        return rc;
    }
    rc = dpublic_hud_service_read_pid(opts->pid_path, &existing);
    if (rc == 0) {
        if (d_handoff_pid_alive(existing)) {
            a90_console_printf("%s start.already_running=1 pid=%ld\r\n",
                               A90_DPUBLIC_HUD_SERVICE_TAG, (long)existing);
            return -EBUSY;
        }
        a90_console_printf("%s start.stale_pid=%ld action=unlink\r\n",
                           A90_DPUBLIC_HUD_SERVICE_RESTART_TAG,
                           (long)existing);
        (void)unlink(opts->pid_path);
        (void)dpublic_hud_service_write_status(opts->status_path,
                                               "stale-cleaned",
                                               existing,
                                               0,
                                               0);
    }

    rc = a90_service_stop(A90_SERVICE_HUD, A90_D_HANDOFF_HUD_TIMEOUT_MS);
    a90_console_printf("%s start.autohud_stop_rc=%d\r\n", A90_DPUBLIC_HUD_SERVICE_TAG, rc);
    if (rc < 0) {
        return rc;
    }

    if (pipe(ready_pipe) < 0) {
        return -errno;
    }
    pid = fork();
    if (pid < 0) {
        rc = -errno;
        (void)close(ready_pipe[0]);
        (void)close(ready_pipe[1]);
        a90_console_printf("%s start.fork_rc=%d\r\n", A90_DPUBLIC_HUD_SERVICE_TAG, rc);
        return rc;
    }
    if (pid == 0) {
        int child_rc;

        (void)close(ready_pipe[0]);
        (void)setsid();
        child_rc = dpublic_hud_service_child_loop(
            opts->intent_path,
            opts->status_path,
            opts->preopen_drm,
            ready_pipe[1]);
        _exit(child_rc == 0 ? 0 : 1);
    }
    if (child_pid_out != NULL) {
        *child_pid_out = pid;
    }
    (void)close(ready_pipe[1]);
    {
        struct pollfd wait_ready = {
            .fd = ready_pipe[0],
            .events = POLLIN | POLLHUP,
        };
        int child_ready_rc = -EIO;
        ssize_t got;
        int poll_rc = poll(&wait_ready, 1, A90_D_HANDOFF_HUD_TIMEOUT_MS);

        got = poll_rc > 0
                  ? read(ready_pipe[0], &child_ready_rc, sizeof(child_ready_rc))
                  : -1;
        (void)close(ready_pipe[0]);
        if (poll_rc <= 0 || got != (ssize_t)sizeof(child_ready_rc) ||
            child_ready_rc < 0) {
            int cleanup_rc;

            rc = child_ready_rc < 0
                     ? child_ready_rc
                     : (poll_rc == 0 ? -ETIMEDOUT : -EIO);
            cleanup_rc = d_handoff_stop_drm_owner(
                A90_DPUBLIC_HUD_SERVICE_TAG,
                pid);
            if (cleanup_rc == 0 && child_pid_out != NULL) {
                *child_pid_out = -1;
            }
            a90_console_printf(
                "%s start.child_ready=0 preopen_drm=%d rc=%d cleanup_rc=%d\r\n",
                A90_DPUBLIC_HUD_SERVICE_TAG,
                opts->preopen_drm ? 1 : 0,
                rc,
                cleanup_rc);
            return cleanup_rc < 0 ? cleanup_rc : rc;
        }
    }

    rc = dpublic_hud_service_write_pid(opts->pid_path, pid);
    a90_console_printf("%s start.intent=%s\r\n", A90_DPUBLIC_HUD_SERVICE_TAG, opts->intent_path);
    a90_console_printf("%s start.pid=%ld\r\n", A90_DPUBLIC_HUD_SERVICE_TAG, (long)pid);
    a90_console_printf("%s start.pidfile=%s rc=%d\r\n",
                       A90_DPUBLIC_HUD_SERVICE_TAG, opts->pid_path, rc);
    if (rc < 0) {
        int cleanup_rc = d_handoff_stop_drm_owner(
            A90_DPUBLIC_HUD_SERVICE_TAG,
            pid);

        if (cleanup_rc == 0 && child_pid_out != NULL) {
            *child_pid_out = -1;
        }
        a90_console_printf(
            "%s start.pidfile_cleanup_rc=%d original_rc=%d\r\n",
            A90_DPUBLIC_HUD_SERVICE_TAG,
            cleanup_rc,
            rc);
        return cleanup_rc < 0 ? cleanup_rc : rc;
    }
    a90_console_printf("%s start.process_model=forked-native-child-survives-switch-root\r\n",
                       A90_DPUBLIC_HUD_SERVICE_TAG);
    a90_console_printf("%s start.preopen_drm=%d child_ready=1\r\n",
                       A90_DPUBLIC_HUD_SERVICE_TAG,
                       opts->preopen_drm ? 1 : 0);
    a90_console_printf("%s start.done=1\r\n", A90_DPUBLIC_HUD_SERVICE_TAG);
    return 0;
}

static int dpublic_hud_service_status(const struct dpublic_hud_service_opts *opts) {
    pid_t pid;
    int rc = dpublic_hud_service_read_pid(opts->pid_path, &pid);
    bool running;
    bool drm_fd;

    if (rc < 0) {
        a90_console_printf("%s status.state=stopped rc=%d\r\n",
                           A90_DPUBLIC_HUD_SERVICE_TAG, rc);
        return 0;
    }
    running = d_handoff_pid_alive(pid);
    drm_fd = running && d_handoff_pid_has_drm_fd(pid);
    a90_console_printf("%s status.state=%s\r\n",
                       A90_DPUBLIC_HUD_SERVICE_TAG, running ? "running" : "stale-pid");
    a90_console_printf("%s status.pid=%ld\r\n", A90_DPUBLIC_HUD_SERVICE_TAG, (long)pid);
    a90_console_printf("%s status.pidfile=%s\r\n", A90_DPUBLIC_HUD_SERVICE_TAG, opts->pid_path);
    a90_console_printf("%s status.status_file=%s\r\n",
                       A90_DPUBLIC_HUD_SERVICE_TAG, opts->status_path);
    a90_console_printf("%s status.intent=%s\r\n", A90_DPUBLIC_HUD_SERVICE_TAG, opts->intent_path);
    a90_console_printf("%s status.drm_fd=%d\r\n", A90_DPUBLIC_HUD_SERVICE_TAG, drm_fd ? 1 : 0);
    a90_console_printf("%s status.debian_direct_kms=0\r\n", A90_DPUBLIC_HUD_SERVICE_TAG);
    a90_console_printf("%s status.intent_dedupe=%s\r\n",
                       A90_DPUBLIC_HUD_SERVICE_DEDUP_TAG,
                       A90_DPUBLIC_HUD_SERVICE_DEDUP_MODE);
    a90_console_printf("%s status.restart_policy=%s\r\n",
                       A90_DPUBLIC_HUD_SERVICE_RESTART_TAG,
                       A90_DPUBLIC_HUD_SERVICE_RESTART_MODE);
    return running ? 0 : -ESRCH;
}

static int dpublic_hud_service_stop_until(
        const struct dpublic_hud_service_opts *opts,
        long deadline_ms) {
    pid_t pid;
    int rc;

    if (d_handoff_deadline_expired(deadline_ms)) {
        return -ETIMEDOUT;
    }
    rc = dpublic_hud_service_read_pid(opts->pid_path, &pid);

    if (rc < 0) {
        a90_console_printf("%s stop.not_running=1 rc=%d\r\n",
                           A90_DPUBLIC_HUD_SERVICE_TAG, rc);
        (void)unlink(opts->pid_path);
        return 0;
    }
    a90_console_printf("%s stop.pid=%ld release_drm=%d\r\n",
                       A90_DPUBLIC_HUD_SERVICE_TAG, (long)pid, opts->release_drm ? 1 : 0);
    rc = d_handoff_stop_drm_owner_until(
        A90_DPUBLIC_HUD_SERVICE_TAG,
        pid,
        deadline_ms);
    (void)unlink(opts->pid_path);
    if (rc == 0) {
        (void)dpublic_hud_service_write_status(opts->status_path, "stopped", pid, 0, 0);
        a90_console_printf("%s stop.done=1\r\n", A90_DPUBLIC_HUD_SERVICE_TAG);
    } else {
        a90_console_printf("%s stop.done=0 rc=%d\r\n", A90_DPUBLIC_HUD_SERVICE_TAG, rc);
    }
    return rc;
}

static int dpublic_hud_service_stop(const struct dpublic_hud_service_opts *opts) {
    return dpublic_hud_service_stop_until(opts, 0);
}

static int dpublic_hud_service_restart(const struct dpublic_hud_service_opts *opts) {
    int stop_rc;
    int start_rc;

    a90_console_printf("%s restart.policy=%s\r\n",
                       A90_DPUBLIC_HUD_SERVICE_RESTART_TAG,
                       A90_DPUBLIC_HUD_SERVICE_RESTART_MODE);
    stop_rc = dpublic_hud_service_stop(opts);
    a90_console_printf("%s restart.stop_rc=%d\r\n",
                       A90_DPUBLIC_HUD_SERVICE_RESTART_TAG,
                       stop_rc);
    if (stop_rc < 0) {
        a90_console_printf("%s restart.done=0 rc=%d\r\n",
                           A90_DPUBLIC_HUD_SERVICE_RESTART_TAG,
                           stop_rc);
        return stop_rc;
    }
    start_rc = dpublic_hud_service_start(opts, NULL);
    a90_console_printf("%s restart.start_rc=%d\r\n",
                       A90_DPUBLIC_HUD_SERVICE_RESTART_TAG,
                       start_rc);
    a90_console_printf("%s restart.done=%d rc=%d\r\n",
                       A90_DPUBLIC_HUD_SERVICE_RESTART_TAG,
                       start_rc == 0 ? 1 : 0,
                       start_rc);
    return start_rc;
}

int a90_server_distro_dpublic_hud_presenter_service_cmd(char **argv, int argc) {
    const char *mode;
    struct dpublic_hud_service_opts opts;
    int rc;

    if (argc < 2) {
        a90_console_printf("usage: dpublic-hud-presenter-service [start|status|stop|restart] [options]\r\n");
        return -EINVAL;
    }
    mode = argv[1];
    rc = dpublic_hud_service_parse_opts(argv, argc, 2, &opts);
    if (rc < 0) {
        a90_console_printf("usage: dpublic-hud-presenter-service [start|status|stop|restart] [options]\r\n");
        a90_console_printf("%s refused=bad-options rc=%d\r\n", A90_DPUBLIC_HUD_SERVICE_TAG, rc);
        return rc;
    }

    a90_console_printf("%s service=native-dpublic-hud-presenter\r\n",
                       A90_DPUBLIC_HUD_SERVICE_TAG);
    a90_console_printf("%s owner=native-init-root\r\n", A90_DPUBLIC_HUD_SERVICE_TAG);
    a90_console_printf("%s survives_handoff=1\r\n", A90_DPUBLIC_HUD_SERVICE_TAG);
    a90_console_printf("%s intent_dedupe=%s\r\n",
                       A90_DPUBLIC_HUD_SERVICE_DEDUP_TAG,
                       A90_DPUBLIC_HUD_SERVICE_DEDUP_MODE);
    a90_console_printf("%s shared_run_dir=%s\r\n",
                       A90_DPUBLIC_HUD_SERVICE_SHARED_TAG,
                       A90_DPUBLIC_HUD_SERVICE_SHARED_MODE);
    a90_console_printf("%s restart_policy=%s\r\n",
                       A90_DPUBLIC_HUD_SERVICE_RESTART_TAG,
                       A90_DPUBLIC_HUD_SERVICE_RESTART_MODE);
    if (strcmp(mode, "start") == 0) {
        return dpublic_hud_service_start(&opts, NULL);
    }
    if (strcmp(mode, "status") == 0) {
        return dpublic_hud_service_status(&opts);
    }
    if (strcmp(mode, "stop") == 0) {
        return dpublic_hud_service_stop(&opts);
    }
    if (strcmp(mode, "restart") == 0) {
        return dpublic_hud_service_restart(&opts);
    }

    a90_console_printf("%s refused=unknown-mode mode=%s\r\n",
                       A90_DPUBLIC_HUD_SERVICE_TAG, mode);
    return -EINVAL;
}

static int d_handoff_stop_drm_owner_until(const char *tag,
                                          pid_t pid,
                                          long deadline_ms) {
    int rc;
    int wait_ms;

    if (d_handoff_deadline_expired(deadline_ms)) {
        return -ETIMEDOUT;
    }

    a90_console_printf("%s handoff_display drm_owner_pid=%ld action=term\r\n", tag, (long)pid);
    if (kill(pid, SIGTERM) < 0 && errno != ESRCH) {
        rc = -errno;
        a90_console_printf("%s handoff_display drm_owner_pid=%ld term_rc=%d\r\n",
                           tag, (long)pid, rc);
        return rc;
    }
    wait_ms = d_handoff_deadline_remaining_ms(
        deadline_ms,
        A90_D_HANDOFF_DRM_OWNER_TIMEOUT_MS);
    if (wait_ms == 0) {
        return -ETIMEDOUT;
    }
    rc = d_handoff_wait_pid_gone(pid, wait_ms);
    if (rc == 0) {
        return 0;
    }

    a90_console_printf("%s handoff_display drm_owner_pid=%ld action=kill\r\n", tag, (long)pid);
    if (kill(pid, SIGKILL) < 0 && errno != ESRCH) {
        rc = -errno;
        a90_console_printf("%s handoff_display drm_owner_pid=%ld kill_rc=%d\r\n",
                           tag, (long)pid, rc);
        return rc;
    }
    wait_ms = d_handoff_deadline_remaining_ms(
        deadline_ms,
        A90_D_HANDOFF_DRM_OWNER_TIMEOUT_MS);
    if (wait_ms == 0) {
        return -ETIMEDOUT;
    }
    rc = d_handoff_wait_pid_gone(pid, wait_ms);
    if (rc < 0) {
        a90_console_printf("%s handoff_display drm_owner_pid=%ld stop_rc=%d\r\n",
                           tag, (long)pid, rc);
    }
    return rc;
}

static int d_handoff_stop_drm_owner(const char *tag, pid_t pid) {
    return d_handoff_stop_drm_owner_until(tag, pid, 0);
}

static int d_handoff_count_display_owners(bool preserve_dpublic,
                                          unsigned int *count_out,
                                          long deadline_ms) {
    DIR *proc;
    struct dirent *entry;
    unsigned int count = 0;
    unsigned int process_entries = 0;

    if (count_out == NULL) {
        return -EINVAL;
    }
    proc = opendir("/proc");
    if (proc == NULL) {
        return -errno;
    }
    while ((entry = readdir(proc)) != NULL) {
        pid_t pid;
        bool has_drm = false;
        int rc;

        if (d_handoff_deadline_expired(deadline_ms)) {
            closedir(proc);
            return -ETIMEDOUT;
        }
        if (d_handoff_parse_pid(entry->d_name, &pid) < 0) {
            continue;
        }
        if (++process_entries > A90_D_HANDOFF_PROC_ENTRY_MAX) {
            closedir(proc);
            return -E2BIG;
        }
        if (!d_handoff_pid_is_native_init(pid)) {
            continue;
        }
        rc = d_handoff_pid_has_drm_fd_until(pid, deadline_ms, &has_drm);
        if (rc < 0) {
            closedir(proc);
            return rc;
        }
        if (!has_drm) {
            continue;
        }
        if (preserve_dpublic && dpublic_hud_service_pid_is_default(pid)) {
            continue;
        }
        count++;
    }
    closedir(proc);
    *count_out = count;
    return 0;
}

static int d_handoff_stop_display_owners_mode(
        const char *tag,
        bool preserve_dpublic,
        struct d3_display_release_proof *proof) {
    DIR *proc;
    struct dirent *entry;
    struct dpublic_hud_service_opts dpublic_opts;
    struct a90_kms_release_result kms_release;
    struct a90_kms_info kms_info;
    unsigned int killed = 0;
    unsigned int owner_attempts = 0;
    unsigned int owner_timeouts = 0;
    unsigned int process_entries = 0;
    unsigned int remaining = 0;
    unsigned int native_pid1_drm_fd_count = 0;
    unsigned int other_drm_fd_count = 0;
    long display_deadline =
        monotonic_millis() + A90_D_HANDOFF_DISPLAY_TOTAL_TIMEOUT_MS;
    int final_rc = 0;
    int scan_rc;
    int service_rc;

    memset(&kms_release, 0, sizeof(kms_release));
    memset(&kms_info, 0, sizeof(kms_info));
    if (proof != NULL) {
        memset(proof, 0, sizeof(*proof));
    }
    a90_console_printf(
        "%s handoff_display total_timeout_ms=%u\r\n",
        tag,
        A90_D_HANDOFF_DISPLAY_TOTAL_TIMEOUT_MS);

    service_rc = d_handoff_deadline_remaining_ms(
        display_deadline,
        A90_D_HANDOFF_HUD_TIMEOUT_MS);
    if (service_rc == 0) {
        final_rc = -ETIMEDOUT;
        goto display_done;
    }
    service_rc = a90_service_stop(A90_SERVICE_HUD, service_rc);
    a90_console_printf("%s handoff_display service=autohud stop_rc=%d\r\n", tag, service_rc);
    if (service_rc < 0) {
        final_rc = service_rc;
    }
    if (d_handoff_deadline_expired(display_deadline)) {
        final_rc = -ETIMEDOUT;
        goto display_done;
    }

    if (!preserve_dpublic) {
        dpublic_hud_service_default_opts(&dpublic_opts);
        dpublic_opts.release_drm = true;
        service_rc = dpublic_hud_service_stop_until(
            &dpublic_opts,
            display_deadline);
        a90_console_printf("%s handoff_display service=dpublic-hud-presenter stop_rc=%d\r\n",
                           tag, service_rc);
        if (service_rc < 0) {
            final_rc = service_rc;
        }
        if (d_handoff_deadline_expired(display_deadline)) {
            final_rc = -ETIMEDOUT;
            goto display_done;
        }
    }

    proc = opendir("/proc");
    if (proc == NULL) {
        final_rc = final_rc < 0 ? final_rc : -errno;
        a90_console_printf("%s handoff_display scan=fail rc=%d\r\n", tag, final_rc);
        return final_rc;
    }
    while ((entry = readdir(proc)) != NULL) {
        pid_t pid;
        bool has_drm = false;
        int rc;

        if (d_handoff_deadline_expired(display_deadline)) {
            final_rc = -ETIMEDOUT;
            break;
        }
        if (d_handoff_parse_pid(entry->d_name, &pid) < 0) {
            continue;
        }
        if (++process_entries > A90_D_HANDOFF_PROC_ENTRY_MAX) {
            final_rc = -E2BIG;
            a90_console_printf(
                "%s handoff_display process_limit=%u scanned=%u stop=refused\r\n",
                tag,
                A90_D_HANDOFF_PROC_ENTRY_MAX,
                process_entries);
            break;
        }
        if (!d_handoff_pid_is_native_init(pid)) {
            continue;
        }
        rc = d_handoff_pid_has_drm_fd_until(
            pid,
            display_deadline,
            &has_drm);
        if (rc < 0) {
            final_rc = rc;
            break;
        }
        if (!has_drm) {
            continue;
        }
        if (preserve_dpublic && dpublic_hud_service_pid_is_default(pid)) {
            a90_console_printf("%s handoff_display drm_owner_pid=%ld action=preserve-dpublic-hud-presenter\r\n",
                               tag, (long)pid);
            continue;
        }
        if (owner_attempts >= A90_D_HANDOFF_DRM_OWNER_MAX) {
            final_rc = -E2BIG;
            a90_console_printf(
                "%s handoff_display owner_limit=%u attempted=%u stop=refused\r\n",
                tag,
                A90_D_HANDOFF_DRM_OWNER_MAX,
                owner_attempts);
            break;
        }
        owner_attempts++;
        rc = d_handoff_stop_drm_owner_until(tag, pid, display_deadline);
        if (!preserve_dpublic && rc == -EBUSY) {
            owner_timeouts++;
        } else if (rc < 0) {
            final_rc = rc;
        } else {
            killed++;
        }
    }
    closedir(proc);
    if (final_rc == -ETIMEDOUT) {
        goto display_done;
    }

    if (!preserve_dpublic) {
        int release_rc = a90_kms_release_for_handoff(&kms_release);

        a90_console_printf(
            "%s native_kms_release rc=%d fd_before=%d "
            "disable_plane_rc=%d disable_crtc_rc=%d "
            "munmap_failures=%u rmfb_failures=%u "
            "destroy_dumb_failures=%u drop_master_rc=%d close_rc=%d "
            "release_complete=%d\r\n",
            A90_D3_DISPLAY_RELEASE_TAG,
            release_rc,
            kms_release.fd_before,
            kms_release.disable_plane_rc,
            kms_release.disable_crtc_rc,
            kms_release.munmap_failures,
            kms_release.rmfb_failures,
            kms_release.destroy_dumb_failures,
            kms_release.drop_master_rc,
            kms_release.close_rc,
            kms_release.release_complete ? 1 : 0);
        if (release_rc < 0) {
            final_rc = kms_release.rc < 0 ? kms_release.rc : -EIO;
        }
        if (d_handoff_deadline_expired(display_deadline)) {
            final_rc = -ETIMEDOUT;
            goto display_done;
        }
    }

    scan_rc = d_handoff_count_display_owners(
        preserve_dpublic,
        &remaining,
        display_deadline);
    if (scan_rc < 0) {
        final_rc = final_rc < 0 ? final_rc : scan_rc;
    } else if (remaining != 0U) {
        final_rc = -EBUSY;
    } else if (owner_timeouts != 0U) {
        a90_console_printf("%s handoff_display owner_timeouts=%u resolved_by_zero_owner_scan=1\r\n",
                           tag, owner_timeouts);
    }
    if (!preserve_dpublic && final_rc != -ETIMEDOUT) {
        scan_rc = d_handoff_count_all_drm_fds(
            getpid(),
            &native_pid1_drm_fd_count,
            &other_drm_fd_count,
            display_deadline);
        a90_kms_info(&kms_info);
        if (scan_rc < 0) {
            final_rc = final_rc < 0 ? final_rc : scan_rc;
        } else if (getpid() != 1 ||
                   native_pid1_drm_fd_count != 0U ||
                   other_drm_fd_count != 0U ||
                   kms_info.initialized) {
            final_rc = -EBUSY;
        }
        a90_console_printf(
            "%s native_pid1_drm_fd_count=0 observed=%u\r\n",
            A90_D3_DISPLAY_RELEASE_TAG,
            native_pid1_drm_fd_count);
        a90_console_printf(
            "%s other_drm_fd_count=0 observed=%u\r\n",
            A90_D3_DISPLAY_RELEASE_TAG,
            other_drm_fd_count);
        a90_console_printf(
            "%s native_kms_initialized=0 observed=%d\r\n",
            A90_D3_DISPLAY_RELEASE_TAG,
            kms_info.initialized ? 1 : 0);
        a90_console_printf(
            "%s display_services_restart_blocked=1 corridor=synchronous-handoff\r\n",
            A90_D3_DISPLAY_RELEASE_TAG);
        if (proof != NULL) {
            proof->valid =
                final_rc == 0 &&
                getpid() == 1 &&
                native_pid1_drm_fd_count == 0U &&
                other_drm_fd_count == 0U &&
                !kms_info.initialized &&
                kms_release.release_complete;
            proof->native_pid1_drm_fd_count = native_pid1_drm_fd_count;
            proof->other_drm_fd_count = other_drm_fd_count;
            proof->native_kms_initialized = kms_info.initialized;
            proof->display_services_restart_blocked = true;
            proof->kms_release = kms_release;
        }
    }
display_done:
    if (final_rc == -ETIMEDOUT) {
        a90_console_printf(
            "%s handoff_display deadline=expired timeout_ms=%u stop=refused\r\n",
            tag,
            A90_D_HANDOFF_DISPLAY_TOTAL_TIMEOUT_MS);
    }
    a90_console_printf("%s handoff_display required_nonpreserved_owner_count=0 observed=%u\r\n",
                       tag, remaining);
    a90_console_printf("%s handoff_display=done killed=%u rc=%d\r\n",
                       tag, killed, final_rc);
    return final_rc;
}

static int d_handoff_stop_display_owners(const char *tag) {
    return d_handoff_stop_display_owners_mode(tag, true, NULL);
}

static int d3_handoff_stop_display_owners_strict(void) {
    a90_console_printf("%s handoff_display strict=1 preserve_dpublic=0\r\n",
                       A90_D3_IMMUTABLE_TAG);
    return d_handoff_stop_display_owners_mode(
        A90_D3_TAG,
        false,
        &d3_last_display_release);
}

static int d3_hex64_valid(const char *s) {
    size_t n = 0;

    if (s == NULL) {
        return 0;
    }
    for (; s[n] != '\0'; ++n) {
        char c = s[n];
        int ok = (c >= '0' && c <= '9') ||
                 (c >= 'a' && c <= 'f') ||
                 (c >= 'A' && c <= 'F');
        if (!ok) {
            return 0;
        }
    }
    return n == 64;
}

static int d3_sha_equal_ci(const char *a, const char *b) {
    int i;

    if (a == NULL || b == NULL) {
        return 0;
    }
    for (i = 0; i < 64; ++i) {
        char ca = a[i];
        char cb = b[i];

        if (ca >= 'A' && ca <= 'Z') {
            ca = (char)(ca + 32);
        }
        if (cb >= 'A' && cb <= 'Z') {
            cb = (char)(cb + 32);
        }
        if (ca == '\0' || ca != cb) {
            return 0;
        }
    }
    return a[64] == '\0' && b[64] == '\0';
}

static int d3_path_clean(const char *path) {
    const char *c;
    size_t root_len;

    if (path == NULL || path[0] == '\0') {
        return 0;
    }
    root_len = strlen(A90_D3_ALLOWED_IMAGE_ROOT);
    if (strncmp(path, A90_D3_ALLOWED_IMAGE_ROOT, root_len) != 0 ||
        path[root_len] == '\0') {
        return 0;
    }
    if (strstr(path, "..") != NULL) {
        return 0;
    }
    for (c = path; *c != '\0'; ++c) {
        if (*c == '\n' || *c == '\r' || *c == '\t') {
            return 0;
        }
    }
    return 1;
}

static int d3_mkdir_p(const char *path, mode_t mode) {
    char tmp[PATH_MAX];
    size_t len;
    char *cursor;

    if (path == NULL || path[0] != '/') {
        return -EINVAL;
    }
    len = strlen(path);
    if (len == 0 || len >= sizeof(tmp)) {
        return -ENAMETOOLONG;
    }
    memcpy(tmp, path, len + 1);
    for (cursor = tmp + 1; *cursor != '\0'; ++cursor) {
        if (*cursor != '/') {
            continue;
        }
        *cursor = '\0';
        if (mkdir(tmp, mode) < 0 && errno != EEXIST) {
            return -errno;
        }
        *cursor = '/';
    }
    if (mkdir(tmp, mode) < 0 && errno != EEXIST) {
        return -errno;
    }
    return 0;
}

struct d3_source_identity {
    int fd;
    dev_t dev;
    ino_t ino;
    off_t size;
    mode_t mode;
    uid_t uid;
    gid_t gid;
    nlink_t nlink;
    struct timespec mtime;
    struct timespec ctime;
};

static int d3_source_stat_matches(const struct d3_source_identity *source,
                                  const struct stat *st) {
    if (source == NULL || st == NULL) {
        return 0;
    }
    return S_ISREG(st->st_mode) &&
           st->st_dev == source->dev &&
           st->st_ino == source->ino &&
           st->st_size == source->size &&
           st->st_mode == source->mode &&
           st->st_uid == source->uid &&
           st->st_gid == source->gid &&
           st->st_nlink == source->nlink &&
           st->st_mtim.tv_sec == source->mtime.tv_sec &&
           st->st_mtim.tv_nsec == source->mtime.tv_nsec &&
           st->st_ctim.tv_sec == source->ctime.tv_sec &&
           st->st_ctim.tv_nsec == source->ctime.tv_nsec;
}

static int d3_open_source(const char *path, struct d3_source_identity *source) {
    int fd;
    struct stat st;
    int saved_errno;

    if (source == NULL) {
        return -EINVAL;
    }
    memset(source, 0, sizeof(*source));
    source->fd = -1;
    fd = open(path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) {
        saved_errno = errno;
        a90_console_printf("%s open=fail path=%s errno=%d (%s)\r\n",
                           A90_D3_TAG, path, saved_errno, strerror(saved_errno));
        return -saved_errno;
    }
    if (fstat(fd, &st) < 0) {
        saved_errno = errno;
        close(fd);
        return -saved_errno;
    }
    if (!S_ISREG(st.st_mode) || st.st_size <= 0) {
        close(fd);
        a90_console_printf("%s stop=not-regular-or-empty path=%s\r\n", A90_D3_TAG, path);
        return -EINVAL;
    }
    source->fd = fd;
    source->dev = st.st_dev;
    source->ino = st.st_ino;
    source->size = st.st_size;
    source->mode = st.st_mode;
    source->uid = st.st_uid;
    source->gid = st.st_gid;
    source->nlink = st.st_nlink;
    source->mtime = st.st_mtim;
    source->ctime = st.st_ctim;
    return 0;
}

static int d3_source_path_matches(const char *path,
                                  const struct d3_source_identity *source) {
    struct stat st;

    if (source == NULL || source->fd < 0) {
        return -EINVAL;
    }
    if (lstat(path, &st) < 0) {
        return -errno;
    }
    if (!d3_source_stat_matches(source, &st)) {
        return -ESTALE;
    }
    return 0;
}

static int d3_source_fd_matches(const struct d3_source_identity *source) {
    struct stat st;

    if (source == NULL || source->fd < 0) {
        return -EINVAL;
    }
    if (fstat(source->fd, &st) < 0) {
        return -errno;
    }
    return d3_source_stat_matches(source, &st) ? 0 : -ESTALE;
}

static int d3_source_receipt_enabled(void) {
    const char *leaf;

    if (strncmp(A90_D3_SOURCE_RECEIPT_PATH,
                A90_D3_SOURCE_RECEIPT_CACHE_ROOT,
                strlen(A90_D3_SOURCE_RECEIPT_CACHE_ROOT)) != 0) {
        return 0;
    }
    leaf = A90_D3_SOURCE_RECEIPT_PATH +
           strlen(A90_D3_SOURCE_RECEIPT_CACHE_ROOT);
    return leaf[0] != '\0' && strchr(leaf, '/') == NULL &&
           strstr(leaf, "..") == NULL &&
           strchr(leaf, '\n') == NULL && strchr(leaf, '\r') == NULL &&
           strlen(A90_D3_SOURCE_RECEIPT_PATH) + strlen(".tmp") < PATH_MAX;
}

static int d3_normalize_sha(char out[65], const char *sha) {
    unsigned int index;

    if (out == NULL || !d3_hex64_valid(sha)) {
        return -EINVAL;
    }
    for (index = 0; index < 64U; ++index) {
        char c = sha[index];

        out[index] = (c >= 'A' && c <= 'Z') ? (char)(c + 32) : c;
    }
    out[64] = '\0';
    return 0;
}

static int d3_format_source_receipt(
    char *out,
    size_t out_size,
    const char *image,
    const char *expected_sha,
    const struct d3_source_identity *source) {
    char normalized_sha[65];
    int length;

    if (out == NULL || source == NULL || !d3_path_clean(image) ||
        d3_normalize_sha(normalized_sha, expected_sha) < 0) {
        return -EINVAL;
    }
    length = snprintf(
        out,
        out_size,
        "schema=%s\n"
        "image=%s\n"
        "sha256=%s\n"
        "dev=%" PRIuMAX "\n"
        "ino=%" PRIuMAX "\n"
        "size=%" PRIdMAX "\n"
        "mode=%" PRIuMAX "\n"
        "uid=%" PRIuMAX "\n"
        "gid=%" PRIuMAX "\n"
        "nlink=%" PRIuMAX "\n"
        "mtime_sec=%" PRIdMAX "\n"
        "mtime_nsec=%" PRIdMAX "\n"
        "ctime_sec=%" PRIdMAX "\n"
        "ctime_nsec=%" PRIdMAX "\n",
        A90_D3_SOURCE_RECEIPT_SCHEMA,
        image,
        normalized_sha,
        (uintmax_t)source->dev,
        (uintmax_t)source->ino,
        (intmax_t)source->size,
        (uintmax_t)source->mode,
        (uintmax_t)source->uid,
        (uintmax_t)source->gid,
        (uintmax_t)source->nlink,
        (intmax_t)source->mtime.tv_sec,
        (intmax_t)source->mtime.tv_nsec,
        (intmax_t)source->ctime.tv_sec,
        (intmax_t)source->ctime.tv_nsec);
    if (length < 0 || (size_t)length >= out_size) {
        return -EOVERFLOW;
    }
    return length;
}

static int d3_fsync_cache_dir(void) {
    int fd;
    int rc = 0;

    fd = open("/cache", O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) {
        return -errno;
    }
    if (fsync(fd) < 0) {
        rc = -errno;
    }
    if (close(fd) < 0 && rc == 0) {
        rc = -errno;
    }
    return rc;
}

static int d3_verify_source_receipt_open(
    const char *image,
    const char *expected_sha,
    const struct d3_source_identity *source) {
    char expected[A90_D3_SOURCE_RECEIPT_MAX];
    char observed[A90_D3_SOURCE_RECEIPT_MAX];
    struct stat before;
    struct stat opened;
    size_t consumed = 0;
    ssize_t extra;
    int expected_size;
    int fd;

    if (!d3_source_receipt_enabled()) {
        return -ENOTSUP;
    }
    if (d3_source_fd_matches(source) < 0 ||
        d3_source_path_matches(image, source) < 0) {
        return -ESTALE;
    }
    expected_size = d3_format_source_receipt(
        expected, sizeof(expected), image, expected_sha, source);
    if (expected_size < 0) {
        return expected_size;
    }
    if (lstat(A90_D3_SOURCE_RECEIPT_PATH, &before) < 0) {
        return -errno;
    }
    if (!S_ISREG(before.st_mode) || S_ISLNK(before.st_mode) ||
        before.st_uid != 0 || before.st_gid != 0 || before.st_nlink != 1 ||
        (before.st_mode & 0777) != 0600 ||
        before.st_size != (off_t)expected_size) {
        return -EPERM;
    }
    fd = open(A90_D3_SOURCE_RECEIPT_PATH,
              O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) {
        return -errno;
    }
    if (fstat(fd, &opened) < 0 ||
        opened.st_dev != before.st_dev || opened.st_ino != before.st_ino ||
        opened.st_size != before.st_size || opened.st_mode != before.st_mode ||
        opened.st_uid != before.st_uid || opened.st_gid != before.st_gid ||
        opened.st_nlink != before.st_nlink || !S_ISREG(opened.st_mode)) {
        int saved = errno != 0 ? errno : ESTALE;

        close(fd);
        return -saved;
    }
    while (consumed < (size_t)expected_size) {
        ssize_t count = read(fd,
                             observed + consumed,
                             (size_t)expected_size - consumed);

        if (count < 0) {
            if (errno == EINTR) {
                continue;
            }
            close(fd);
            return -errno;
        }
        if (count == 0) {
            close(fd);
            return -ESTALE;
        }
        consumed += (size_t)count;
    }
    do {
        extra = read(fd, observed, 1U);
    } while (extra < 0 && errno == EINTR);
    if (close(fd) < 0 && extra == 0) {
        return -errno;
    }
    if (extra != 0 ||
        memcmp(observed, expected, (size_t)expected_size) != 0) {
        return -ESTALE;
    }
    return 0;
}

static int d3_write_source_receipt(
    const char *image,
    const char *expected_sha,
    const struct d3_source_identity *source) {
    char content[A90_D3_SOURCE_RECEIPT_MAX];
    char temporary[PATH_MAX];
    struct stat st;
    int content_size;
    int fd;
    int rc = 0;

    if (!d3_source_receipt_enabled()) {
        return -ENOTSUP;
    }
    content_size = d3_format_source_receipt(
        content, sizeof(content), image, expected_sha, source);
    if (content_size < 0) {
        return content_size;
    }
    snprintf(temporary, sizeof(temporary), "%s.tmp", A90_D3_SOURCE_RECEIPT_PATH);
    if (lstat(temporary, &st) == 0) {
        if (!S_ISREG(st.st_mode) || st.st_uid != 0 || st.st_gid != 0 ||
            st.st_nlink != 1 || (st.st_mode & 0777) != 0600) {
            return -EPERM;
        }
        if (unlink(temporary) < 0) {
            return -errno;
        }
    } else if (errno != ENOENT) {
        return -errno;
    }
    if (lstat(A90_D3_SOURCE_RECEIPT_PATH, &st) == 0) {
        if (!S_ISREG(st.st_mode) || st.st_uid != 0 || st.st_gid != 0 ||
            st.st_nlink != 1 || (st.st_mode & 0777) != 0600) {
            return -EPERM;
        }
    } else if (errno != ENOENT) {
        return -errno;
    }
    fd = open(temporary,
              O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC | O_NOFOLLOW,
              0600);
    if (fd < 0) {
        return -errno;
    }
    if (fchown(fd, 0, 0) < 0 || fchmod(fd, 0600) < 0 ||
        write_all_checked(fd, content, (size_t)content_size) < 0 ||
        fsync(fd) < 0) {
        rc = errno != 0 ? -errno : -EIO;
    }
    if (close(fd) < 0 && rc == 0) {
        rc = -errno;
    }
    if (rc == 0 && rename(temporary, A90_D3_SOURCE_RECEIPT_PATH) < 0) {
        rc = -errno;
    }
    if (rc == 0) {
        rc = d3_fsync_cache_dir();
    }
    if (rc < 0) {
        (void)unlink(temporary);
        (void)d3_fsync_cache_dir();
        return rc;
    }
    return d3_verify_source_receipt_open(image, expected_sha, source);
}

static int d3_path_is_mounted(const char *mountpoint) {
    FILE *fp;
    char source[PATH_MAX];
    char target[PATH_MAX];
    char fstype[64];
    int mounted = 0;

    fp = fopen("/proc/mounts", "r");
    if (fp == NULL) {
        return -errno;
    }
    while (fscanf(fp, "%1023s %1023s %63s %*s %*d %*d\n", source, target, fstype) == 3) {
        (void)source;
        (void)fstype;
        if (strcmp(target, mountpoint) == 0) {
            mounted = 1;
            break;
        }
    }
    fclose(fp);
    return mounted;
}

static int d3_read_loop_major(unsigned int *major_out) {
    FILE *fp;
    unsigned int major_num = 0;
    char name[64];
    char line[256];

    if (major_out == NULL) {
        return -EINVAL;
    }
    fp = fopen("/proc/devices", "r");
    if (fp == NULL) {
        return -errno;
    }
    while (fgets(line, sizeof(line), fp) != NULL) {
        if (sscanf(line, " %u %63s", &major_num, name) != 2) {
            continue;
        }
        if (strcmp(name, "loop") == 0) {
            *major_out = major_num;
            fclose(fp);
            return 0;
        }
    }
    fclose(fp);
    return -ENOENT;
}

static int d3_ensure_loop_node(bool *created_out) {
    struct stat st;
    unsigned int loop_major = 0;
    int rc;

    if (created_out != NULL) {
        *created_out = false;
    }
    if (lstat(A90_D3_LOOP, &st) == 0) {
        if (!S_ISBLK(st.st_mode)) {
            return -EINVAL;
        }
        return 0;
    }
    if (errno != ENOENT) {
        return -errno;
    }
    rc = d3_read_loop_major(&loop_major);
    if (rc < 0) {
        return rc;
    }
    if (mknod(A90_D3_LOOP, S_IFBLK | 0600, makedev(loop_major, 0)) < 0) {
        return -errno;
    }
    if (created_out != NULL) {
        *created_out = true;
    }
    a90_console_printf("%s loop_node_created=1 major=%u node=%s\r\n",
                       A90_D3_TAG, loop_major, A90_D3_LOOP);
    return 0;
}

static int d3_run_busybox(char *const argv[], int timeout_ms) {
    struct a90_run_config config;
    struct a90_run_result result;
    pid_t pid = -1;
    int rc;

    memset(&config, 0, sizeof(config));
    config.tag = "server-distro-d3";
    config.argv = argv;
    config.stdio_mode = A90_RUN_STDIO_CONSOLE;
    config.timeout_ms = timeout_ms;
    config.stop_timeout_ms = 2000;

    rc = a90_run_spawn(&config, &pid);
    if (rc < 0) {
        return rc;
    }
    rc = a90_run_wait(pid, &config, &result);
    if (rc < 0) {
        return rc;
    }
    return a90_run_result_to_rc(&result);
}

static int d3_attach_loop(const char *image,
                          const struct d3_source_identity *source,
                          bool *attached_out) {
    /*
     * -r attaches read-only, so the kernel refuses a write to the source
     * through this loop device even if a later mount asked for one. The
     * source's immutability stops being a convention held up by copying it
     * and becomes a property the kernel enforces.
     */
    struct loop_info64 requested;
    struct loop_info64 observed;
    struct stat loop_st;
    int loop_fd;
    int rc;

    if (source == NULL || source->fd < 0) {
        return -EINVAL;
    }
    rc = d3_source_path_matches(image, source);
    if (rc < 0) {
        return rc;
    }
    loop_fd = open(A90_D3_LOOP, O_RDWR | O_CLOEXEC | O_NOFOLLOW);
    if (loop_fd < 0) {
        return -errno;
    }
    if (fstat(loop_fd, &loop_st) < 0) {
        rc = -errno;
        close(loop_fd);
        return rc;
    }
    if (!S_ISBLK(loop_st.st_mode)) {
        close(loop_fd);
        return -EINVAL;
    }
    if (ioctl(loop_fd, LOOP_SET_FD, source->fd) < 0) {
        rc = -errno;
        close(loop_fd);
        return rc;
    }
    memset(&requested, 0, sizeof(requested));
    requested.lo_flags = LO_FLAGS_READ_ONLY;
    snprintf((char *)requested.lo_file_name,
             sizeof(requested.lo_file_name),
             "%s",
             image);
    if (ioctl(loop_fd, LOOP_SET_STATUS64, &requested) < 0) {
        rc = -errno;
        (void)ioctl(loop_fd, LOOP_CLR_FD, 0);
        close(loop_fd);
        return rc;
    }
    memset(&observed, 0, sizeof(observed));
    if (ioctl(loop_fd, LOOP_GET_STATUS64, &observed) < 0) {
        rc = -errno;
        (void)ioctl(loop_fd, LOOP_CLR_FD, 0);
        close(loop_fd);
        return rc;
    }
    if (observed.lo_device != (uint64_t)source->dev ||
        observed.lo_inode != (uint64_t)source->ino ||
        (observed.lo_flags & LO_FLAGS_READ_ONLY) == 0) {
        (void)ioctl(loop_fd, LOOP_CLR_FD, 0);
        close(loop_fd);
        return -ESTALE;
    }
    close(loop_fd);
    if (attached_out != NULL) {
        *attached_out = true;
    }
    a90_console_printf(
        "%s loop_backing_identity=verified dev_ino=match read_only=1\r\n",
        A90_D3_IMMUTABLE_TAG);
    a90_console_printf("%s loop=attached node=%s image=%s\r\n",
                       A90_D3_TAG, A90_D3_LOOP, image);
    return 0;
}

static int d3_detach_loop(void) {
    char *const argv[] = {
        (char *)A90_D3_BUSYBOX,
        (char *)"losetup",
        (char *)"-d",
        (char *)A90_D3_LOOP,
        NULL,
    };
    int rc = d3_run_busybox(argv, A90_D3_SWITCH_TIMEOUT_MS);

    return rc == 0 ? 0 : -EIO;
}

static int d3_mount_root(void) {
    char *const argv[] = {
        (char *)A90_D3_BUSYBOX,
        (char *)"mount",
        (char *)"-t",
        (char *)"ext4",
        (char *)"-o",
        (char *)"ro",
        (char *)A90_D3_LOOP,
        (char *)A90_D3_ROOT,
        NULL,
    };
    int rc = d3_run_busybox(argv, A90_D3_SWITCH_TIMEOUT_MS);

    if (rc != 0) {
        a90_console_printf("%s mount=fail rc=%d root=%s\r\n", A90_D3_TAG, rc, A90_D3_ROOT);
        return rc > 0 ? -EIO : rc;
    }
    a90_console_printf("%s rootfs=mounted root=%s loop=%s\r\n",
                       A90_D3_TAG, A90_D3_ROOT, A90_D3_LOOP);
    return 0;
}

static int d3_verify_source_sha_fd(const struct d3_source_identity *source,
                                   const char *expected_sha,
                                   const char *phase) {
    static unsigned char buffer[32768];
    static const char hex[] = "0123456789abcdef";
    struct a90_sha256_ctx context;
    struct stat before;
    struct stat after;
    unsigned char digest[32];
    char actual_sha[65];
    off_t offset = 0;
    unsigned int index;

    if (source == NULL || source->fd < 0 ||
        fstat(source->fd, &before) < 0 ||
        !d3_source_stat_matches(source, &before)) {
        a90_console_printf("%s source_sha phase=%s compute=fail\r\n",
                           A90_D3_IMMUTABLE_TAG, phase);
        return -ESTALE;
    }
    a90_helper_sha256_init(&context);
    while (offset < source->size) {
        size_t want = (size_t)(source->size - offset);
        ssize_t got;

        if (want > sizeof(buffer)) {
            want = sizeof(buffer);
        }
        got = pread(source->fd, buffer, want, offset);
        if (got < 0) {
            if (errno == EINTR) {
                continue;
            }
            return -errno;
        }
        if (got == 0) {
            return -ESTALE;
        }
        a90_helper_sha256_update(&context, buffer, (size_t)got);
        offset += got;
    }
    if (fstat(source->fd, &after) < 0 ||
        !d3_source_stat_matches(source, &after)) {
        return -ESTALE;
    }
    a90_helper_sha256_final(&context, digest);
    for (index = 0; index < sizeof(digest); ++index) {
        actual_sha[index * 2U] = hex[digest[index] >> 4U];
        actual_sha[index * 2U + 1U] = hex[digest[index] & 0x0fU];
    }
    actual_sha[64] = '\0';
    if (!d3_sha_equal_ci(actual_sha, expected_sha)) {
        a90_console_printf("%s source_sha phase=%s sha=%s expected_sha_match=0\r\n",
                           A90_D3_IMMUTABLE_TAG, phase, actual_sha);
        return -ESTALE;
    }
    a90_console_printf("%s source_sha phase=%s sha=%s expected_sha_match=1\r\n",
                       A90_D3_IMMUTABLE_TAG, phase, actual_sha);
    return 0;
}

int a90_server_distro_source_receipt_preflight(const char *image,
                                               const char *expected_sha) {
    struct d3_source_identity source;
    int rc;

    if (!d3_source_receipt_enabled()) {
        return 0;
    }
    if (!d3_path_clean(image) || !d3_hex64_valid(expected_sha)) {
        return -EINVAL;
    }
    rc = d3_open_source(image, &source);
    if (rc < 0) {
        return rc;
    }
    rc = d3_verify_source_receipt_open(image, expected_sha, &source);
    close(source.fd);
    if (rc == 0) {
        a90_console_printf(
            "%s source_receipt=verified path=%s metadata=exact full_sha=skipped\r\n",
            A90_D3_IMMUTABLE_TAG,
            A90_D3_SOURCE_RECEIPT_PATH);
    }
    return rc;
}

int a90_server_distro_source_receipt_ensure(const char *image,
                                            const char *expected_sha) {
    struct d3_source_identity source;
    int rc;

    if (!d3_source_receipt_enabled()) {
        return 0;
    }
    if (!d3_path_clean(image) || !d3_hex64_valid(expected_sha)) {
        return -EINVAL;
    }
    rc = d3_open_source(image, &source);
    if (rc < 0) {
        return rc;
    }
    rc = d3_verify_source_receipt_open(image, expected_sha, &source);
    if (rc == 0) {
        rc = d3_fsync_cache_dir();
    }
    if (rc == 0) {
        a90_console_printf(
            "%s source_receipt=retained path=%s metadata=exact full_sha=skipped\r\n",
            A90_D3_IMMUTABLE_TAG,
            A90_D3_SOURCE_RECEIPT_PATH);
        close(source.fd);
        return 0;
    }
    a90_console_printf(
        "%s source_receipt=qualifying path=%s prior_rc=%d full_sha=required\r\n",
        A90_D3_IMMUTABLE_TAG,
        A90_D3_SOURCE_RECEIPT_PATH,
        rc);
    rc = d3_verify_source_sha_fd(&source, expected_sha, "receipt-qualification");
    if (rc == 0) {
        rc = d3_write_source_receipt(image, expected_sha, &source);
    }
    close(source.fd);
    if (rc < 0) {
        a90_console_printf("%s source_receipt=qualification-failed rc=%d\r\n",
                           A90_D3_IMMUTABLE_TAG,
                           rc);
        return rc;
    }
    a90_console_printf(
        "%s source_receipt=qualified path=%s metadata=exact full_sha=verified\r\n",
        A90_D3_IMMUTABLE_TAG,
        A90_D3_SOURCE_RECEIPT_PATH);
    return 0;
}

/*
 * Cover each writable path with its own tmpfs over the read-only root.
 *
 * Mounted after the root so each tmpfs shadows the image's directory rather
 * than the other way round. Every mount is inside A90_D3_ROOT, so a failure
 * leaves the read-only root and the source untouched.
 */
static int d3_mount_writable_set(unsigned *mounted_out) {
    unsigned index;

    if (mounted_out == NULL) {
        return -EINVAL;
    }
    for (index = 0; index < A90_D3_WRITABLE_SET_MAX; ++index) {
        char target[256];
        int written = snprintf(target,
                               sizeof(target),
                               "%s%s",
                               A90_D3_ROOT,
                               a90_d3_writable_set[index].path);

        if (written < 0 || (size_t)written >= sizeof(target)) {
            return -ENAMETOOLONG;
        }
        if (mount("a90-d3-writable",
                  target,
                  "tmpfs",
                  MS_NOSUID | MS_NODEV,
                  a90_d3_writable_set[index].options) < 0) {
            a90_console_printf("%s writable_set=mount-fail path=%s errno=%d\r\n",
                               A90_D3_IMMUTABLE_TAG,
                               a90_d3_writable_set[index].path,
                               errno);
            return -errno;
        }
        *mounted_out = index + 1U;
    }
    a90_console_printf("%s writable_set=mounted count=%u\r\n",
                       A90_D3_IMMUTABLE_TAG, *mounted_out);
    return 0;
}

/*
 * Prove every writable path really is writable, and the root really is not,
 * before the irreversible step.
 *
 * A missed path would otherwise surface as Debian failing somewhere after
 * switch_root, which costs an ordinal and is hard to attribute. Failing here
 * costs nothing: native-init stays native and names the path.
 */
static int d3_verify_writable_set(void) {
    char probe[256];
    unsigned index;
    int written;
    int fd;

    written = snprintf(probe, sizeof(probe), "%s/.a90-d3-ro-probe", A90_D3_ROOT);
    if (written < 0 || (size_t)written >= sizeof(probe)) {
        return -ENAMETOOLONG;
    }
    fd = open(probe, O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC | O_NOFOLLOW, 0600);
    if (fd >= 0) {
        close(fd);
        (void)unlink(probe);
        a90_console_printf("%s writable_set=root-not-read-only path=%s\r\n",
                           A90_D3_IMMUTABLE_TAG, A90_D3_ROOT);
        return -EPERM;
    }
    if (errno != EROFS) {
        a90_console_printf("%s writable_set=root-probe-errno errno=%d\r\n",
                           A90_D3_IMMUTABLE_TAG, errno);
        return -errno;
    }

    for (index = 0; index < A90_D3_WRITABLE_SET_MAX; ++index) {
        written = snprintf(probe,
                           sizeof(probe),
                           "%s%s/.a90-d3-rw-probe",
                           A90_D3_ROOT,
                           a90_d3_writable_set[index].path);
        if (written < 0 || (size_t)written >= sizeof(probe)) {
            return -ENAMETOOLONG;
        }
        fd = open(probe,
                  O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC | O_NOFOLLOW,
                  0600);
        if (fd < 0) {
            a90_console_printf("%s writable_set=not-writable path=%s errno=%d\r\n",
                               A90_D3_IMMUTABLE_TAG,
                               a90_d3_writable_set[index].path,
                               errno);
            return -errno;
        }
        close(fd);
        if (unlink(probe) < 0) {
            return -errno;
        }
    }
    a90_console_printf("%s writable_set=verified root=read-only count=%u\r\n",
                       A90_D3_IMMUTABLE_TAG, A90_D3_WRITABLE_SET_MAX);
    return 0;
}


static int d3_remove_work_image(bool owned) {
    if (!owned) {
        return 0;
    }
    if (unlink(A90_D3_WORK_IMAGE) < 0 && errno != ENOENT) {
        int rc = -errno;

        a90_console_printf("%s work_copy=cleanup-fail rc=%d path=%s\r\n",
                           A90_D3_IMMUTABLE_TAG, rc, A90_D3_WORK_IMAGE);
        return rc;
    }
    a90_console_printf("%s work_copy=removed path=%s\r\n",
                       A90_D3_IMMUTABLE_TAG, A90_D3_WORK_IMAGE);
    return 0;
}

static int d3_join(char *out, size_t out_size, const char *root, const char *leaf) {
    int n = snprintf(out, out_size, "%s/%s", root, leaf);

    if (n < 0 || (size_t)n >= out_size) {
        return -ENAMETOOLONG;
    }
    return 0;
}

#if A90_UFS_OBSERVER_AUTH_OVERLAY_V1
static int h17_authorized_key_bytes_valid(const char *data, size_t size) {
    static const char prefix[] = "ssh-ed25519 ";
    size_t index;
    bool payload_seen = false;

    if (data == NULL || size < 64U || size > A90_H17_AUTH_MAX_BYTES ||
        size < sizeof(prefix) ||
        memcmp(data, prefix, sizeof(prefix) - 1U) != 0 ||
        data[size - 1U] != '\n') {
        return -EINVAL;
    }
    for (index = sizeof(prefix) - 1U; index + 1U < size; ++index) {
        unsigned char ch = (unsigned char)data[index];

        if (ch == ' ') {
            if (!payload_seen) {
                return -EINVAL;
            }
            break;
        }
        if (!((ch >= 'A' && ch <= 'Z') ||
              (ch >= 'a' && ch <= 'z') ||
              (ch >= '0' && ch <= '9') ||
              ch == '+' || ch == '/' || ch == '=')) {
            return -EINVAL;
        }
        payload_seen = true;
    }
    for (; index + 1U < size; ++index) {
        unsigned char ch = (unsigned char)data[index];

        if (ch < 0x20U || ch > 0x7eU || ch == '\r' || ch == '\n') {
            return -EINVAL;
        }
    }
    return payload_seen ? 0 : -EINVAL;
}

static int h17_mount_observer_auth(bool *mounted_out) {
    char target_dir[PATH_MAX];
    char target_key[PATH_MAX];
    char source_data[A90_H17_AUTH_MAX_BYTES + 1U];
    char verify_data[A90_H17_AUTH_MAX_BYTES + 1U];
    struct stat source_st;
    struct stat target_st;
    int source_fd = -1;
    int target_fd = -1;
    int dir_fd = -1;
    ssize_t source_size;
    ssize_t verify_size;
    int rc;

    if (mounted_out == NULL) {
        return -EINVAL;
    }
    *mounted_out = false;
    source_fd = open(A90_H17_OBSERVER_AUTH_SOURCE,
                     O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (source_fd < 0 || fstat(source_fd, &source_st) < 0) {
        rc = -errno;
        goto out;
    }
    if (!S_ISREG(source_st.st_mode) || S_ISLNK(source_st.st_mode) ||
        source_st.st_nlink != 1 ||
        (source_st.st_mode & 0777) != 0400 ||
        source_st.st_size < 64 ||
        source_st.st_size > (off_t)A90_H17_AUTH_MAX_BYTES) {
        rc = -EPERM;
        goto out;
    }
    source_size = read(source_fd, source_data, sizeof(source_data));
    if (source_size != source_st.st_size ||
        h17_authorized_key_bytes_valid(source_data, (size_t)source_size) < 0) {
        rc = -EINVAL;
        goto out;
    }
    rc = d3_join(target_dir, sizeof(target_dir), A90_D3_ROOT, "root/.ssh");
    if (rc < 0) {
        goto out;
    }
    if (lstat(target_dir, &target_st) < 0 ||
        !S_ISDIR(target_st.st_mode) || S_ISLNK(target_st.st_mode)) {
        rc = -EPERM;
        goto out;
    }
    if (mount("a90-h17-observer-auth",
              target_dir,
              "tmpfs",
              MS_NOSUID | MS_NODEV | MS_NOEXEC,
              "mode=0700,uid=0,gid=0,size=64k") < 0) {
        rc = -errno;
        goto out;
    }
    *mounted_out = true;
    rc = d3_join(target_key, sizeof(target_key), target_dir, "authorized_keys");
    if (rc < 0) {
        goto out;
    }
    target_fd = open(target_key,
                     O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC | O_NOFOLLOW,
                     0600);
    if (target_fd < 0 ||
        fchown(target_fd, 0, 0) < 0 ||
        fchmod(target_fd, 0600) < 0 ||
        write_all_checked(target_fd, source_data, (size_t)source_size) < 0 ||
        fsync(target_fd) < 0) {
        rc = errno != 0 ? -errno : -EIO;
        goto out;
    }
    if (close(target_fd) < 0) {
        target_fd = -1;
        rc = -errno;
        goto out;
    }
    target_fd = open(target_key, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (target_fd < 0 || fstat(target_fd, &target_st) < 0 ||
        !S_ISREG(target_st.st_mode) || target_st.st_uid != 0 ||
        target_st.st_gid != 0 || target_st.st_nlink != 1 ||
        (target_st.st_mode & 0777) != 0600 ||
        target_st.st_size != source_size) {
        rc = -EPERM;
        goto out;
    }
    verify_size = read(target_fd, verify_data, sizeof(verify_data));
    if (verify_size != source_size ||
        memcmp(source_data, verify_data, (size_t)source_size) != 0) {
        rc = -ESTALE;
        goto out;
    }
    dir_fd = open(target_dir, O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW);
    if (dir_fd < 0 || fsync(dir_fd) < 0) {
        rc = -errno;
        goto out;
    }
    a90_console_printf(
        "%s observer_auth=ready source=boot-private target=/root/.ssh "
        "authorized_keys_mode=0600 bytes=%lld ufs_write=0\r\n",
        A90_H17_TAG,
        (long long)source_size);
    rc = 0;
out:
    if (dir_fd >= 0) {
        (void)close(dir_fd);
    }
    if (target_fd >= 0) {
        (void)close(target_fd);
    }
    if (source_fd >= 0) {
        (void)close(source_fd);
    }
    if (rc < 0 && *mounted_out) {
        if (umount2(target_dir, MNT_DETACH) < 0) {
            return -errno;
        }
        *mounted_out = false;
    }
    return rc;
}

static int h17_unmount_observer_auth(void) {
    char target[PATH_MAX];
    int rc = d3_join(target, sizeof(target), A90_D3_ROOT, "root/.ssh");

    if (rc < 0) {
        return rc;
    }
    return umount2(target, MNT_DETACH) < 0 ? -errno : 0;
}
#endif

static int d3_check_distro_init(void) {
    char init_path[PATH_MAX];
    struct stat st;
    int rc = d3_join(init_path, sizeof(init_path), A90_D3_ROOT, "sbin/init");

    if (rc < 0) {
        return rc;
    }
    if (stat(init_path, &st) < 0) {
        return -errno;
    }
    if (!S_ISREG(st.st_mode) || (st.st_mode & 0111) == 0) {
        return -EINVAL;
    }
    a90_console_printf("%s distro_init=ok path=%s mode=%o\r\n",
                       A90_D3_TAG, init_path, (unsigned int)(st.st_mode & 0777));
    return 0;
}

static int d3_write_display_release_marker(
        const struct d3_display_release_proof *proof) {
    char marker_path[PATH_MAX];
    char marker[1024];
    size_t offset = 0;
    size_t marker_size;
    int fd;
    int rc;
    int n;

    if (proof == NULL || !proof->valid ||
        proof->native_pid1_drm_fd_count != 0U ||
        proof->other_drm_fd_count != 0U ||
        proof->native_kms_initialized ||
        !proof->display_services_restart_blocked ||
        !proof->kms_release.release_complete) {
        return -EPERM;
    }
    rc = d3_join(
        marker_path,
        sizeof(marker_path),
        A90_D3_ROOT,
        A90_D3_DISPLAY_RELEASE_MARKER);
    if (rc < 0) {
        return rc;
    }
    n = snprintf(
        marker,
        sizeof(marker),
        "schema=a90-native-display-release-v1\n"
        "native_pid1_drm_fd_count=%u\n"
        "other_drm_fd_count=%u\n"
        "native_kms_initialized=%d\n"
        "display_services_restart_blocked=%d\n"
        "release_complete=%d\n",
        proof->native_pid1_drm_fd_count,
        proof->other_drm_fd_count,
        proof->native_kms_initialized ? 1 : 0,
        proof->display_services_restart_blocked ? 1 : 0,
        proof->kms_release.release_complete ? 1 : 0);
    if (n < 0 || (size_t)n >= sizeof(marker)) {
        return -EOVERFLOW;
    }
    marker_size = (size_t)n;
    fd = open(
        marker_path,
        O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC | O_NOFOLLOW,
        0600);
    if (fd < 0) {
        return -errno;
    }
    while (offset < marker_size) {
        ssize_t written = write(fd, marker + offset, marker_size - offset);

        if (written < 0) {
            if (errno == EINTR) {
                continue;
            }
            rc = -errno;
            close(fd);
            (void)unlink(marker_path);
            return rc;
        }
        if (written == 0) {
            close(fd);
            (void)unlink(marker_path);
            return -EIO;
        }
        offset += (size_t)written;
    }
    if (close(fd) < 0) {
        rc = -errno;
        (void)unlink(marker_path);
        return rc;
    }
    a90_console_printf(
        "%s release_marker=ready path=%s bytes=%zu\r\n",
        A90_D3_DISPLAY_RELEASE_TAG,
        marker_path,
        marker_size);
    return 0;
}

/*
 * Bind the durable evidence directory onto the new root's /mnt.
 *
 * Without this the collector Debian runs cannot reach the record at all: only
 * /proc, /sys and /dev cross the switch, so a path under the native /mnt/sdext
 * resolves inside the read-only image after switch_root and every write fails
 * silently. A bind is used rather than a move so the SD stays mounted for
 * native, and only this directory is exposed -- not the source image.
 */
static int d3_bind_evidence_dir(bool *bound_out) {
    char dst[PATH_MAX];
    struct stat st;
    int rc;

    if (bound_out != NULL) {
        *bound_out = false;
    }
    /*
     * Both ends must be real directories, not symlinks. d3_mkdir_p accepts an
     * existing entry without checking its type, so a planted symlink at either
     * end could redirect the bind to a wider runtime directory and carry it
     * across the switch. Refuse rather than widen what crosses.
     */
    if (lstat(A90_D3_EVIDENCE_DIR, &st) == 0) {
        if (!S_ISDIR(st.st_mode)) {
            a90_console_printf("%s evidence_bind=src-not-directory path=%s\r\n",
                               A90_D3_IMMUTABLE_TAG, A90_D3_EVIDENCE_DIR);
            return -ENOTDIR;
        }
    } else if (errno != ENOENT) {
        return -errno;
    } else {
        rc = d3_mkdir_p(A90_D3_EVIDENCE_DIR, 0755);
        if (rc < 0) {
            a90_console_printf("%s evidence_bind=mkdir-fail rc=%d path=%s\r\n",
                               A90_D3_IMMUTABLE_TAG, rc, A90_D3_EVIDENCE_DIR);
            return rc;
        }
    }
    rc = d3_join(dst, sizeof(dst), A90_D3_ROOT, A90_D3_EVIDENCE_LEAF);
    if (rc < 0) {
        return rc;
    }
    if (lstat(dst, &st) < 0 || !S_ISDIR(st.st_mode)) {
        a90_console_printf("%s evidence_bind=dst-not-directory path=%s\r\n",
                           A90_D3_IMMUTABLE_TAG, dst);
        return -ENOTDIR;
    }
    /*
     * A normal directory is not a mountpoint, so MS_PRIVATE on it returns
     * EINVAL. Make a temporary self-bind first, require the propagation
     * change to succeed, clone that private mount to Debian, then remove only
     * the temporary source mount. The namespace was made recursively private
     * before any H7 mount, so even the self-bind event cannot escape it.
     */
    if (mount(A90_D3_EVIDENCE_DIR,
              A90_D3_EVIDENCE_DIR,
              NULL,
              MS_BIND,
              NULL) < 0) {
        rc = -errno;
        a90_console_printf("%s evidence_bind=source-self-bind-fail rc=%d\r\n",
                           A90_D3_IMMUTABLE_TAG, rc);
        return rc;
    }
    if (mount(NULL, A90_D3_EVIDENCE_DIR, NULL, MS_PRIVATE, NULL) < 0) {
        rc = -errno;
        a90_console_printf("%s evidence_bind=source-private-fail rc=%d\r\n",
                           A90_D3_IMMUTABLE_TAG, rc);
        (void)umount2(A90_D3_EVIDENCE_DIR, MNT_DETACH);
        return rc;
    }
    a90_console_printf("%s evidence_bind=source-private\r\n",
                       A90_D3_IMMUTABLE_TAG);
    if (mount(A90_D3_EVIDENCE_DIR, dst, NULL, MS_BIND, NULL) < 0) {
        rc = -errno;
        a90_console_printf("%s evidence_bind=fail rc=%d src=%s dst=%s\r\n",
                           A90_D3_IMMUTABLE_TAG, rc, A90_D3_EVIDENCE_DIR, dst);
        (void)umount2(A90_D3_EVIDENCE_DIR, MNT_DETACH);
        return rc;
    }
    if (umount2(A90_D3_EVIDENCE_DIR, MNT_DETACH) < 0) {
        rc = -errno;
        a90_console_printf("%s evidence_bind=source-self-unmount-fail rc=%d\r\n",
                           A90_D3_IMMUTABLE_TAG, rc);
        (void)umount2(dst, MNT_DETACH);
        return rc;
    }
    if (mount(NULL, dst, NULL,
              MS_REMOUNT | MS_BIND | MS_NOSUID | MS_NODEV, NULL) < 0) {
        rc = -errno;
        a90_console_printf("%s evidence_bind=harden-fail rc=%d dst=%s\r\n",
                           A90_D3_IMMUTABLE_TAG, rc, dst);
        (void)umount2(dst, MNT_DETACH);
        return rc;
    }
    if (bound_out != NULL) {
        *bound_out = true;
    }
    a90_console_printf("%s evidence_bind=ok src=%s dst=%s debian_view=/%s\r\n",
                       A90_D3_IMMUTABLE_TAG, A90_D3_EVIDENCE_DIR, dst,
                       A90_D3_EVIDENCE_LEAF);
    return 0;
}

/*
 * Expose only the redacted native Wi-Fi handoff surface to Debian. Credentials,
 * supplicant control sockets, and native logs remain below /cache/a90-wifi and
 * never cross switch_root. The bind is read-only from Debian while native may
 * continue publishing carrier/DNS state through the source directory.
 */
static int d3_validate_wifi_handoff_members(void) {
    DIR *dir;
    struct dirent *entry;
    int rc = 0;

    dir = opendir(A90_D3_WIFI_HANDOFF_DIR);
    if (dir == NULL) {
        return -errno;
    }
    errno = 0;
    while ((entry = readdir(dir)) != NULL) {
        char path[PATH_MAX];
        struct stat st;
        off_t max_size;

        if (strcmp(entry->d_name, ".") == 0 ||
            strcmp(entry->d_name, "..") == 0) {
            continue;
        }
        if (strcmp(entry->d_name, "status") == 0) {
            max_size = 512;
        } else if (strcmp(entry->d_name, "resolv.conf") == 0) {
            max_size = 4096;
        } else if (strcmp(entry->d_name, "companion") == 0) {
            max_size = 512;
        } else {
            a90_console_printf(
                "%s wifi_handoff_bind=unexpected-member name=%s\r\n",
                A90_D3_IMMUTABLE_TAG,
                entry->d_name);
            rc = -EPERM;
            break;
        }
        if (snprintf(path,
                     sizeof(path),
                     "%s/%s",
                     A90_D3_WIFI_HANDOFF_DIR,
                     entry->d_name) >= (int)sizeof(path)) {
            rc = -ENAMETOOLONG;
            break;
        }
        if (lstat(path, &st) < 0) {
            rc = -errno;
            break;
        }
        if (!S_ISREG(st.st_mode) || st.st_uid != 0 || st.st_gid != 0 ||
            (st.st_mode & 0777) != 0600 || st.st_nlink != 1 ||
            st.st_size <= 0 || st.st_size > max_size) {
            a90_console_printf(
                "%s wifi_handoff_bind=member-unsafe name=%s\r\n",
                A90_D3_IMMUTABLE_TAG,
                entry->d_name);
            rc = -EPERM;
            break;
        }
        errno = 0;
    }
    if (rc == 0 && errno != 0) {
        rc = -errno;
    }
    if (closedir(dir) < 0 && rc == 0) {
        rc = -errno;
    }
    return rc;
}

static int d3_bind_wifi_handoff_dir(bool *bound_out) {
    char dst[PATH_MAX];
    struct stat st;
    int rc;

    if (bound_out != NULL) {
        *bound_out = false;
    }
    if (lstat(A90_D3_WIFI_HANDOFF_DIR, &st) == 0) {
        if (!S_ISDIR(st.st_mode) || st.st_uid != 0 ||
            (st.st_mode & (S_IWGRP | S_IWOTH)) != 0) {
            a90_console_printf("%s wifi_handoff_bind=src-unsafe path=%s\r\n",
                               A90_D3_IMMUTABLE_TAG,
                               A90_D3_WIFI_HANDOFF_DIR);
            return -EPERM;
        }
    } else if (errno != ENOENT) {
        return -errno;
    } else {
        rc = d3_mkdir_p(A90_D3_WIFI_HANDOFF_DIR, 0700);
        if (rc < 0) {
            return rc;
        }
        if (chmod(A90_D3_WIFI_HANDOFF_DIR, 0700) < 0) {
            return -errno;
        }
    }
    rc = d3_validate_wifi_handoff_members();
    if (rc < 0) {
        return rc;
    }
    rc = d3_join(dst, sizeof(dst), A90_D3_ROOT, A90_D3_WIFI_HANDOFF_LEAF);
    if (rc < 0) {
        return rc;
    }
    rc = d3_mkdir_p(dst, 0755);
    if (rc < 0) {
        return rc;
    }
    if (lstat(dst, &st) < 0 || !S_ISDIR(st.st_mode)) {
        a90_console_printf("%s wifi_handoff_bind=dst-not-directory path=%s\r\n",
                           A90_D3_IMMUTABLE_TAG,
                           dst);
        return -ENOTDIR;
    }
    if (mount(A90_D3_WIFI_HANDOFF_DIR,
              A90_D3_WIFI_HANDOFF_DIR,
              NULL,
              MS_BIND,
              NULL) < 0) {
        return -errno;
    }
    if (mount(NULL, A90_D3_WIFI_HANDOFF_DIR, NULL, MS_PRIVATE, NULL) < 0) {
        rc = -errno;
        (void)umount2(A90_D3_WIFI_HANDOFF_DIR, MNT_DETACH);
        return rc;
    }
    if (mount(A90_D3_WIFI_HANDOFF_DIR, dst, NULL, MS_BIND, NULL) < 0) {
        rc = -errno;
        (void)umount2(A90_D3_WIFI_HANDOFF_DIR, MNT_DETACH);
        return rc;
    }
    if (umount2(A90_D3_WIFI_HANDOFF_DIR, MNT_DETACH) < 0) {
        rc = -errno;
        (void)umount2(dst, MNT_DETACH);
        return rc;
    }
    if (mount(NULL,
              dst,
              NULL,
              MS_REMOUNT | MS_BIND | MS_RDONLY | MS_NOSUID | MS_NODEV | MS_NOEXEC,
              NULL) < 0) {
        rc = -errno;
        (void)umount2(dst, MNT_DETACH);
        return rc;
    }
    if (bound_out != NULL) {
        *bound_out = true;
    }
    a90_console_printf(
        "%s wifi_handoff_bind=ok src=%s dst=%s debian_view=/%s mode=ro redacted=1\r\n",
        A90_D3_IMMUTABLE_TAG,
        A90_D3_WIFI_HANDOFF_DIR,
        dst,
        A90_D3_WIFI_HANDOFF_LEAF);
    return 0;
}

static int d3_move_mount_one(const char *src, const char *leaf) {
    char dst[PATH_MAX];
    int rc = d3_join(dst, sizeof(dst), A90_D3_ROOT, leaf);

    if (rc < 0) {
        return rc;
    }
    rc = d3_mkdir_p(dst, 0755);
    if (rc < 0) {
        return rc;
    }
    if (mount(src, dst, NULL, MS_MOVE, NULL) < 0) {
        return -errno;
    }
    a90_console_printf("%s mount_move=%s->%s ok=1\r\n", A90_D3_TAG, src, dst);
    return 0;
}

static int d3_ensure_char_node_at(const char *path, mode_t mode, unsigned int maj, unsigned int min) {
    struct stat st;
    dev_t dev = makedev(maj, min);

    if (lstat(path, &st) == 0) {
        if (S_ISCHR(st.st_mode) && st.st_rdev == dev) {
            (void)chmod(path, mode);
            return 0;
        }
        if (unlink(path) < 0) {
            return -errno;
        }
    } else if (errno != ENOENT) {
        return -errno;
    }
    if (mknod(path, S_IFCHR | mode, dev) < 0) {
        return -errno;
    }
    (void)chmod(path, mode);
    return 0;
}

static int d3_prepare_dev_node(const char *leaf, mode_t mode, unsigned int maj, unsigned int min) {
    char path[PATH_MAX];
    int rc = d3_join(path, sizeof(path), A90_D3_ROOT, leaf);

    if (rc < 0) {
        return rc;
    }
    return d3_ensure_char_node_at(path, mode, maj, min);
}

static int d3_prepare_optional_ttygs0(void) {
    struct stat st;

    if (stat("/dev/ttyGS0", &st) < 0) {
        a90_console_printf("%s dev_node_optional=/dev/ttyGS0 missing errno=%d\r\n",
                           A90_D3_TAG, errno);
        return 0;
    }
    if (!S_ISCHR(st.st_mode)) {
        a90_console_printf("%s dev_node_optional=/dev/ttyGS0 not-char\r\n", A90_D3_TAG);
        return 0;
    }
    return d3_prepare_dev_node("dev/ttyGS0", 0600, major(st.st_rdev), minor(st.st_rdev));
}

static int d3_prepare_new_dev(bool *mounted_devpts) {
    char dev_dir[PATH_MAX];
    char pts_dir[PATH_MAX];
    struct stat st;
    bool dev_tmpfs_mounted = false;
    bool devpts_mounted = false;
    int rc;

    if (mounted_devpts != NULL) {
        *mounted_devpts = false;
    }
    rc = d3_join(dev_dir, sizeof(dev_dir), A90_D3_ROOT, "dev");
    if (rc < 0) {
        return rc;
    }
    if (lstat(dev_dir, &st) < 0) {
        rc = -errno;
        a90_console_printf("%s dev_tmpfs=refused missing-root-dir rc=%d path=%s\r\n",
                           A90_D3_IMMUTABLE_TAG, rc, dev_dir);
        return rc;
    }
    if (!S_ISDIR(st.st_mode)) {
        a90_console_printf("%s dev_tmpfs=refused root-not-directory path=%s\r\n",
                           A90_D3_IMMUTABLE_TAG, dev_dir);
        return -ENOTDIR;
    }
    if (mount("tmpfs", dev_dir, "tmpfs", MS_NOSUID | MS_NOEXEC, "mode=0755") < 0) {
        rc = -errno;
        a90_console_printf("%s dev_tmpfs=mount-fail rc=%d path=%s\r\n",
                           A90_D3_IMMUTABLE_TAG, rc, dev_dir);
        return rc;
    }
    dev_tmpfs_mounted = true;
    a90_console_printf(
        "%s dev_mountpoint=0 dev_tmpfs=mounted image_write=0 root=%s\r\n",
        A90_D3_IMMUTABLE_TAG,
        dev_dir);
    rc = d3_prepare_dev_node("dev/console", 0600, 5, 1);
    if (rc < 0) {
        goto fail_new_dev;
    }
    rc = d3_prepare_dev_node("dev/tty", 0666, 5, 0);
    if (rc < 0) {
        goto fail_new_dev;
    }
    rc = d3_prepare_dev_node("dev/ptmx", 0666, 5, 2);
    if (rc < 0) {
        goto fail_new_dev;
    }
    rc = d3_prepare_dev_node("dev/null", 0666, 1, 3);
    if (rc < 0) {
        goto fail_new_dev;
    }
    rc = d3_prepare_dev_node("dev/zero", 0666, 1, 5);
    if (rc < 0) {
        goto fail_new_dev;
    }
    rc = d3_prepare_dev_node("dev/random", 0666, 1, 8);
    if (rc < 0) {
        goto fail_new_dev;
    }
    rc = d3_prepare_dev_node("dev/urandom", 0666, 1, 9);
    if (rc < 0) {
        goto fail_new_dev;
    }
    rc = d3_prepare_optional_ttygs0();
    if (rc < 0) {
        goto fail_new_dev;
    }
    rc = d3_join(pts_dir, sizeof(pts_dir), A90_D3_ROOT, "dev/pts");
    if (rc < 0) {
        goto fail_new_dev;
    }
    rc = d3_mkdir_p(pts_dir, 0755);
    if (rc < 0) {
        goto fail_new_dev;
    }
    if (mount("devpts", pts_dir, "devpts", 0, "mode=620,ptmxmode=666") == 0) {
        devpts_mounted = true;
        if (mounted_devpts != NULL) {
            *mounted_devpts = true;
        }
        a90_console_printf("%s devpts=mounted path=%s\r\n", A90_D3_TAG, pts_dir);
    } else {
        a90_console_printf("%s devpts=warn rc=-%d (%s)\r\n",
                           A90_D3_TAG, errno, strerror(errno));
    }
    a90_console_printf("%s dev_mountpoint=0 dev_nodes=prepared root=%s\r\n",
                       A90_D3_TAG, dev_dir);
    return 0;

fail_new_dev:
    if (devpts_mounted) {
        (void)umount2(pts_dir, MNT_DETACH);
    }
    if (mounted_devpts != NULL) {
        *mounted_devpts = false;
    }
    if (dev_tmpfs_mounted && umount2(dev_dir, MNT_DETACH) < 0) {
        a90_console_printf("%s dev_tmpfs=cleanup-fail errno=%d path=%s\r\n",
                           A90_D3_IMMUTABLE_TAG, errno, dev_dir);
        return -EBUSY;
    }
    return rc;
}

static int d3_restore_mount_one(const char *leaf, const char *dst) {
    char src[PATH_MAX];
    int rc;

    rc = d3_join(src, sizeof(src), A90_D3_ROOT, leaf);
    if (rc < 0) {
        return rc;
    }
    if (mount(src, dst, NULL, MS_MOVE, NULL) < 0) {
        rc = -errno;
        a90_console_printf(
            "%s mount_restore=%s->%s fail=1 rc=%d errno=%d (%s)\r\n",
            A90_D3_IMMUTABLE_TAG,
            src,
            dst,
            rc,
            -rc,
            strerror(-rc));
        return rc;
    }
    a90_console_printf("%s mount_restore=%s->%s ok=1\r\n",
                       A90_D3_IMMUTABLE_TAG,
                       src,
                       dst);
    return 0;
}

static int d3_unmount_leaf(const char *leaf) {
    char path[PATH_MAX];
    int rc;

    rc = d3_join(path, sizeof(path), A90_D3_ROOT, leaf);
    if (rc < 0) {
        return rc;
    }
    if (umount2(path, MNT_DETACH) < 0) {
        rc = -errno;
        a90_console_printf(
            "%s mount_restore_unmount=%s fail=1 rc=%d errno=%d (%s)\r\n",
            A90_D3_IMMUTABLE_TAG,
            path,
            rc,
            -rc,
            strerror(-rc));
        return rc;
    }
    a90_console_printf("%s mount_restore_unmount=%s ok=1\r\n",
                       A90_D3_IMMUTABLE_TAG,
                       path);
    return 0;
}

static int d3_move_core_mounts(bool force_private_dev,
                               bool *moved_proc,
                               bool *moved_sys,
                               bool *moved_dev,
                               bool *mounted_new_dev,
                               bool *mounted_devpts) {
    int dev_mounted;
    int rc;

    if (moved_proc != NULL) {
        *moved_proc = false;
    }
    if (moved_sys != NULL) {
        *moved_sys = false;
    }
    if (moved_dev != NULL) {
        *moved_dev = false;
    }
    if (mounted_new_dev != NULL) {
        *mounted_new_dev = false;
    }
    if (mounted_devpts != NULL) {
        *mounted_devpts = false;
    }
    dev_mounted = d3_path_is_mounted("/dev");
    if (dev_mounted < 0) {
        return dev_mounted;
    }
    rc = d3_move_mount_one("/proc", "proc");
    if (rc < 0) {
        return rc;
    }
    if (moved_proc != NULL) {
        *moved_proc = true;
    }
    rc = d3_move_mount_one("/sys", "sys");
    if (rc < 0) {
        return rc;
    }
    if (moved_sys != NULL) {
        *moved_sys = true;
    }
    if (dev_mounted && !force_private_dev) {
        rc = d3_move_mount_one("/dev", "dev");
        if (rc < 0) {
            return rc;
        }
        if (moved_dev != NULL) {
            *moved_dev = true;
        }
    } else {
        char userdata_node[PATH_MAX];

        rc = d3_prepare_new_dev(mounted_devpts);
        if (rc < 0) {
            return rc;
        }
        if (mounted_new_dev != NULL) {
            *mounted_new_dev = true;
        }
        if (force_private_dev) {
            rc = d3_join(userdata_node,
                         sizeof(userdata_node),
                         A90_D3_ROOT,
                         "dev/block/a90-userdata");
            if (rc < 0) {
                return rc;
            }
            if (lstat(userdata_node, &(struct stat){0}) == 0 || errno != ENOENT) {
                a90_console_printf(
                    "%s private_dev=fail userdata_node_exposed=1 path=%s\r\n",
                    A90_D3_IMMUTABLE_TAG,
                    userdata_node);
                return -EPERM;
            }
            a90_console_printf(
                "%s private_dev=ok userdata_node_exposed=0 path=%s\r\n",
                A90_D3_IMMUTABLE_TAG,
                userdata_node);
        }
    }
    return 0;
}

static int d3_restore_core_mounts(bool moved_proc,
                                  bool moved_sys,
                                  bool moved_dev,
                                  bool mounted_new_dev,
                                  bool mounted_devpts) {
    int first_rc = 0;
    int rc;

    if (mounted_devpts) {
        rc = d3_unmount_leaf("dev/pts");
        if (rc < 0 && first_rc == 0) {
            first_rc = rc;
        }
    }
    if (moved_dev) {
        rc = d3_restore_mount_one("dev", "/dev");
        if (rc < 0 && first_rc == 0) {
            first_rc = rc;
        }
    } else if (mounted_new_dev) {
        rc = d3_unmount_leaf("dev");
        if (rc < 0 && first_rc == 0) {
            first_rc = rc;
        }
    }
    if (moved_sys) {
        rc = d3_restore_mount_one("sys", "/sys");
        if (rc < 0 && first_rc == 0) {
            first_rc = rc;
        }
    }
    if (moved_proc) {
        rc = d3_restore_mount_one("proc", "/proc");
        if (rc < 0 && first_rc == 0) {
            first_rc = rc;
        }
    }
    a90_console_printf("%s mount_restore_complete=%d rc=%d\r\n",
                       A90_D3_IMMUTABLE_TAG,
                       first_rc == 0 ? 1 : 0,
                       first_rc);
    return first_rc;
}

int a90_server_distro_switch_root_cmd(char **argv, int argc) {
    const char *image;
    const char *expected_sha;
    int rc;
    struct d3_source_identity source;
    bool loop_created = false;
    bool loop_attached = false;
    bool work_owned = false;
    unsigned writable_mounted = 0;
    bool evidence_bound = false;
    bool cleanup_clean = true;
    bool wifi_handoff_bound = false;
    bool root_mounted = false;
    bool moved_proc = false;
    bool moved_sys = false;
    bool moved_dev = false;
    bool mounted_new_dev = false;
    bool mounted_devpts = false;
    int mounted;
    bool source_receipt_fast;
    char *const newenv[] = {
        (char *)"HOME=/root",
        (char *)"PATH=/sbin:/bin:/usr/sbin:/usr/bin",
        (char *)"TERM=linux",
        NULL,
    };
    char *const switch_argv[] = {
        (char *)A90_D3_BUSYBOX,
        (char *)"switch_root",
        (char *)A90_D3_ROOT,
        (char *)A90_D3_INIT,
        NULL,
    };

    if (argc != 4 || strcmp(argv[1], A90_D3_TOKEN) != 0) {
        a90_console_printf("usage: switch-root-to-distro %s <image> <sha256>\r\n",
                           A90_D3_TOKEN);
        a90_console_printf("%s refused=missing-or-wrong-token-or-argc argc=%d\r\n",
                           A90_D3_TAG, argc);
        return -EPERM;
    }
    image = argv[2];
    expected_sha = argv[3];
    if (!d3_path_clean(image)) {
        a90_console_printf("%s refused=path-outside-approved-sd-runtime image=%s\r\n",
                           A90_D3_TAG, image);
        return -EPERM;
    }
    if (!d3_hex64_valid(expected_sha)) {
        a90_console_printf("%s refused=bad-expected-sha\r\n", A90_D3_TAG);
        return -EINVAL;
    }

    a90_console_printf("%s begin image=%s root=%s\r\n", A90_D3_TAG, image, A90_D3_ROOT);
#if A90_AUTO_HANDOFF_BENCHMARK_V1
    a90_benchmark_emit("handoff_begin");
#endif
    rc = d3_open_source(image, &source);
    if (rc < 0) {
        return rc;
    }
    source_receipt_fast = d3_source_receipt_enabled() != 0;
    rc = source_receipt_fast
             ? d3_verify_source_receipt_open(image, expected_sha, &source)
             : d3_verify_source_sha_fd(&source, expected_sha, "initial");
    if (rc < 0) {
        a90_console_printf("%s stop=source-integrity-initial rc=%d mode=%s\r\n",
                           A90_D3_TAG,
                           rc,
                           source_receipt_fast ? "receipt" : "full-sha");
        close(source.fd);
        return rc;
    }
    if (source_receipt_fast) {
        a90_console_printf(
            "%s source_integrity phase=initial mode=receipt metadata=exact full_sha=skipped\r\n",
            A90_D3_IMMUTABLE_TAG);
    }
#if A90_AUTO_HANDOFF_BENCHMARK_V1
    a90_benchmark_emit(source_receipt_fast
                           ? "source_receipt_initial_done"
                           : "source_sha_initial_done");
#endif

    rc = d3_mkdir_p(A90_D3_ROOT, 0755);
    if (rc < 0) {
        a90_console_printf("%s mkdir_root=fail rc=%d root=%s\r\n", A90_D3_TAG, rc, A90_D3_ROOT);
        goto fail_immutable_source;
    }
    mounted = d3_path_is_mounted(A90_D3_ROOT);
    if (mounted < 0) {
        rc = mounted;
        goto fail_immutable_source;
    }
    if (mounted) {
        a90_console_printf("%s stop=root-already-mounted root=%s\r\n", A90_D3_TAG, A90_D3_ROOT);
        rc = -EBUSY;
        goto fail_immutable_source;
    }
    rc = d3_handoff_stop_display_owners_strict();
    if (rc < 0) {
        a90_console_printf("%s stop=handoff-display-owner rc=%d\r\n", A90_D3_TAG, rc);
        goto fail_immutable_source;
    }
#if A90_AUTO_HANDOFF_BENCHMARK_V1
    a90_benchmark_mark("display_release_done");
#endif
    rc = source_receipt_fast
             ? d3_source_fd_matches(&source)
             : d3_verify_source_sha_fd(
                   &source,
                   expected_sha,
                   "post-display-cleanup");
    if (rc == 0 && source_receipt_fast) {
        rc = d3_source_path_matches(image, &source);
    }
    if (rc < 0) {
        a90_console_printf("%s stop=source-changed-during-display-cleanup rc=%d\r\n",
                           A90_D3_TAG, rc);
        goto fail_immutable_source;
    }
    if (source_receipt_fast) {
        a90_console_printf(
            "%s source_integrity phase=post-display-cleanup mode=identity metadata=exact full_sha=skipped\r\n",
            A90_D3_IMMUTABLE_TAG);
    }
#if A90_AUTO_HANDOFF_BENCHMARK_V1
    a90_benchmark_emit(source_receipt_fast
                           ? "source_identity_post_display_done"
                           : "source_sha_post_display_done");
#endif
    if (mount(NULL, "/", NULL, MS_REC | MS_PRIVATE, NULL) < 0) {
        rc = -errno;
        a90_console_printf("%s mount_namespace=private-fail rc=%d\r\n",
                           A90_D3_IMMUTABLE_TAG, rc);
        goto fail_immutable_source;
    }
    a90_console_printf("%s mount_namespace=private\r\n",
                       A90_D3_IMMUTABLE_TAG);
    rc = d3_ensure_loop_node(&loop_created);
    if (rc < 0) {
        a90_console_printf("%s loop_node=fail rc=%d\r\n", A90_D3_TAG, rc);
        goto fail_immutable_source;
    }
    rc = d3_attach_loop(image, &source, &loop_attached);
    if (rc < 0) {
        goto fail_before_move;
    }
#if A90_AUTO_HANDOFF_BENCHMARK_V1
    a90_benchmark_mark("loop_attached");
#endif
    rc = d3_mount_root();
    if (rc < 0) {
        goto fail_before_move;
    }
    root_mounted = true;
#if A90_AUTO_HANDOFF_BENCHMARK_V1
    a90_benchmark_mark("root_mounted");
#endif
    rc = d3_mount_writable_set(&writable_mounted);
    if (rc < 0) {
        goto fail_before_move;
    }
    rc = d3_verify_writable_set();
    if (rc < 0) {
        goto fail_before_move;
    }
    rc = d3_bind_evidence_dir(&evidence_bound);
    if (rc < 0) {
        goto fail_before_move;
    }
    rc = d3_bind_wifi_handoff_dir(&wifi_handoff_bound);
    if (rc < 0) {
        a90_console_printf("%s stop=wifi-handoff-bind rc=%d\r\n", A90_D3_TAG, rc);
        goto fail_before_move;
    }
#if A90_AUTO_HANDOFF_BENCHMARK_V1
    a90_benchmark_emit("writable_set_ready");
#endif
    rc = d3_check_distro_init();
    if (rc < 0) {
        a90_console_printf("%s stop=distro-init-invalid rc=%d\r\n", A90_D3_TAG, rc);
        goto fail_before_move;
    }
#if A90_AUTO_HANDOFF_BENCHMARK_V1
    a90_benchmark_mark("distro_init_verified");
#endif
    rc = d3_write_display_release_marker(&d3_last_display_release);
    if (rc < 0) {
        a90_console_printf(
            "%s stop=display-release-marker rc=%d\r\n",
            A90_D3_TAG,
            rc);
        goto fail_before_move;
    }
#if A90_AUTO_HANDOFF_BENCHMARK_V1
    a90_benchmark_mark("display_marker_ready");
#endif
    rc = d3_move_core_mounts(
        false,
        &moved_proc,
        &moved_sys,
        &moved_dev,
        &mounted_new_dev,
        &mounted_devpts);
    if (rc < 0) {
        int restore_rc = d3_restore_core_mounts(
            moved_proc,
            moved_sys,
            moved_dev,
            mounted_new_dev,
            mounted_devpts);

        a90_console_printf("%s mount_move=fail rc=%d\r\n", A90_D3_TAG, rc);
        if (restore_rc < 0) {
            cleanup_clean = false;
            rc = restore_rc;
        } else {
            moved_proc = false;
            moved_sys = false;
            moved_dev = false;
            mounted_new_dev = false;
            mounted_devpts = false;
        }
        goto fail_before_move;
    }
#if A90_AUTO_HANDOFF_BENCHMARK_V1
    a90_benchmark_mark("mount_moves_done");
#endif

    a90_console_printf("%s exec_switch_root_now busybox=%s root=%s init=%s console=reuse-stdio\r\n",
                       A90_D3_TAG, A90_D3_BUSYBOX, A90_D3_ROOT, A90_D3_INIT);
    a90_logf("server-distro",
             "D3 switch_root exec source=%s root=%s mode=ro writable_set=%u"
             " evidence_bound=%d wifi_handoff_bound=%d",
             image,
             A90_D3_ROOT,
             writable_mounted,
             evidence_bound ? 1 : 0,
             wifi_handoff_bound ? 1 : 0);
#if A90_AUTO_HANDOFF_BENCHMARK_V1
    a90_benchmark_mark("switch_root_exec");
#endif
    sync();
    usleep(200000);
    execve(A90_D3_BUSYBOX, switch_argv, newenv);

    rc = -errno;
    a90_console_printf("%s execve_switch_root=fail rc=%d errno=%d (%s)\r\n",
                       A90_D3_TAG, rc, -rc, strerror(-rc));
    {
        int restore_rc = d3_restore_core_mounts(
            moved_proc,
            moved_sys,
            moved_dev,
            mounted_new_dev,
            mounted_devpts);

        if (restore_rc < 0) {
            cleanup_clean = false;
            rc = restore_rc;
        } else {
            moved_proc = false;
            moved_sys = false;
            moved_dev = false;
            mounted_new_dev = false;
            mounted_devpts = false;
        }
    }

fail_before_move:
    /*
     * Cleanup outcomes were discarded here, so a leaked loop attachment or a
     * surviving mount could poison the next ordinal while the run still
     * reported source_unchanged. The image hash proves the source bytes; it
     * says nothing about mount state, so record that separately.
     */
    if (root_mounted && cleanup_clean) {
        if (umount2(A90_D3_ROOT, MNT_DETACH) == 0) {
            a90_console_printf("%s rootfs=unmounted-after-fail root=%s\r\n",
                               A90_D3_TAG, A90_D3_ROOT);
            root_mounted = false;
        } else {
            cleanup_clean = false;
            a90_console_printf("%s rootfs=unmount-fail root=%s errno=%d\r\n",
                               A90_D3_TAG, A90_D3_ROOT, errno);
        }
    } else if (root_mounted) {
        a90_console_printf(
            "%s rootfs=retained-after-restore-fail root=%s recovery_required=1\r\n",
            A90_D3_TAG,
            A90_D3_ROOT);
    }
    if (loop_attached && !root_mounted) {
        int detach_rc = d3_detach_loop();

        if (detach_rc == 0) {
            loop_attached = false;
        } else {
            cleanup_clean = false;
            a90_console_printf("%s loop=detach-fail node=%s rc=%d\r\n",
                               A90_D3_TAG, A90_D3_LOOP, detach_rc);
        }
    } else if (loop_attached) {
        cleanup_clean = false;
        a90_console_printf(
            "%s loop=retained-with-root node=%s recovery_required=1\r\n",
            A90_D3_TAG,
            A90_D3_LOOP);
    }
    if (loop_created) {
        /* Only remove the node this run created, and only once it is free. */
        if (loop_attached) {
            cleanup_clean = false;
        } else if (unlink(A90_D3_LOOP) < 0 && errno != ENOENT) {
            cleanup_clean = false;
            a90_console_printf("%s loop_node=unlink-fail node=%s errno=%d\r\n",
                               A90_D3_TAG, A90_D3_LOOP, errno);
        }
    }
    a90_console_printf("%s mount_state_clean_after_failure=%d\r\n",
                       A90_D3_IMMUTABLE_TAG, cleanup_clean ? 1 : 0);
fail_immutable_source:
    (void)d3_remove_work_image(work_owned);
    if (d3_source_path_matches(image, &source) < 0 ||
        d3_verify_source_sha_fd(&source, expected_sha, "after-failure") < 0) {
        a90_console_printf("%s source_unchanged_after_failure=0 stop=source-identity-lost\r\n",
                           A90_D3_IMMUTABLE_TAG);
        close(source.fd);
        return -ESTALE;
    }
    a90_console_printf("%s source_unchanged_after_failure=1\r\n",
                       A90_D3_IMMUTABLE_TAG);
    close(source.fd);
#if A90_AUTO_HANDOFF_BENCHMARK_V1
    a90_benchmark_emit("handoff_failed_native");
#endif
    return rc;
}

#define A90_D4_TAG "A90D4"
#define A90_D4_TOKEN "SERVER-DISTRO-D4-USERDATA-APPLIANCE"
#define A90_D4_ALLOWED_SOURCE_ROOT "/mnt/sdext/a90/runtime/"
#define A90_D4_NODE "/dev/block/a90-userdata"
#define A90_D4_ROOT "/mnt/a90-userdata-root"
#define A90_D4_BUSYBOX "/bin/busybox"
#define A90_D4_INIT "/sbin/init"
#define A90_D4_MARKER_LEAF "etc/a90-appliance-stage"
#define A90_D4_MARKER_VALUE "userdata=appliance-root"
#define A90_D4_E2FS_TOOLROOT "/mnt/sdext/a90/runtime/d4c-format-toolroot"
#define A90_D4_E2FS_MKE2FS_HOST A90_D4_E2FS_TOOLROOT "/usr/sbin/mke2fs"
#define A90_D4_E2FS_MKFS_EXT4_HOST A90_D4_E2FS_TOOLROOT "/usr/sbin/mkfs.ext4"
#define A90_D4_E2FS_DUMPE2FS_HOST A90_D4_E2FS_TOOLROOT "/usr/sbin/dumpe2fs"
#define A90_D4_E2FS_TUNE2FS_HOST A90_D4_E2FS_TOOLROOT "/usr/sbin/tune2fs"
#define A90_D4_E2FS_MKE2FS_SHA "92721c9a402ba8015ec6321acffaac187ce32fd2772a54690b46dfe94b8f6589"
#define A90_D4_E2FS_DUMPE2FS_SHA "6e22ed6668e336a891621de3e18b8915e56545351c20c06bafb6682ac1de9aae"
#define A90_D4_E2FS_TUNE2FS_SHA "f4bd3a7e56772236ec0dd8f6a4c5fa2b9dfa52cf70d2af0fa1eb50cfeafa34ad"
#define A90_D4_E2FS_MKFS_EXT4_CHROOT "/usr/sbin/mkfs.ext4"
#define A90_D4_E2FS_DUMPE2FS_CHROOT "/usr/sbin/dumpe2fs"
#define A90_D4_MIN_BYTES 100000000000ULL
#define A90_D4_MAX_BYTES 140000000000ULL
#define A90_D4_EXPECTED_PARTNAME "userdata"
#define A90_D4_FORMAT_TIMEOUT_MS 120000
#define A90_D4_POPULATE_TIMEOUT_MS 300000
#define A90_D4_SWITCH_TIMEOUT_MS 30000
#define A90_D4_FORMATTER_PROBE_MIN_BYTES 4194304ULL
#define A90_D4_FORMATTER_PROBE_MAX_BYTES 67108864ULL
#define A90_D4_EXT4_MAGIC_OFFSET 1080
#define A90_D4_EXT_STATE_OFFSET 1082
#define A90_D4_EXT_FEATURE_COMPAT_OFFSET 1116
#define A90_D4_EXT_FEATURE_INCOMPAT_OFFSET 1120
#define A90_D4_EXT_UUID_OFFSET 1128
#define A90_D4_EXT_LABEL_OFFSET 1144
#define A90_D4_EXT_UUID_BYTES 16U
#define A90_D4_EXT_LABEL_BYTES 16U
#define A90_D4_EXT_COMPAT_HAS_JOURNAL 0x00000004U
#define A90_D4_EXT_INCOMPAT_RECOVER 0x00000004U
#define A90_D4_EXT_VALID_FS 0x0001U
#define A90_D4_EXPECTED_INIT_SIZE 68448
#define A90_D4_H14_UUID "300aaf21-412c-4238-9106-56414eaab105"
#define A90_D4_H14_CONTENT_MANIFEST_SHA256 \
    "e1950058627446d6bbd487d6a17b80f5766be4956b54cb56659b541dab09f8f6"

enum d4_ro_content_kind {
    D4_RO_CONTENT_REGULAR = 1,
    D4_RO_CONTENT_SYMLINK = 2,
};

struct d4_ro_content_identity {
    const char *leaf;
    enum d4_ro_content_kind kind;
    unsigned int mode;
    unsigned int uid;
    unsigned int gid;
    long long size;
    const char *sha256;
    const char *link_target;
};

static const struct d4_ro_content_identity d4_h14_content[] = {
    { "usr/sbin/init", D4_RO_CONTENT_REGULAR, 0755, 0, 0, 68448,
      "402c5e6daeae7f19f01040ba17657f43c14ef6570316ec34a06c6bb87ab923f2", NULL },
    { "etc/inittab", D4_RO_CONTENT_REGULAR, 0644, 0, 0, 123,
      "fb98929887e704aeba715458aa9226ceffa7fdd6f3f53590c367727a51fc96c1", NULL },
    { "etc/a90-d3-firstboot", D4_RO_CONTENT_REGULAR, 0755, 0, 0, 12092,
      "fd8625402c76b2ee0cc4a2aff07eed3b182c6dd12eba1a022a445ea428c8c84a", NULL },
    { "etc/a90-appliance-stage", D4_RO_CONTENT_REGULAR, 0644, 0, 0, 24,
      "3b8effc761c3662f3cc60059c5918e6388106d260f03a110a00f84e06a601a73", NULL },
    { "etc/a90-server-distro-stage", D4_RO_CONTENT_REGULAR, 0644, 0, 0, 1570,
      "68752627d9eae6d372c37f8dd545fb3ac93144b056cfae2cdff1c8a13160421a", NULL },
    { "etc/debian_version", D4_RO_CONTENT_REGULAR, 0644, 0, 0, 6,
      "f4366c3f4617e36754fdb11f429f7e7f73998db823ee7d3c7145070e7472339d", NULL },
    { "usr/bin/ip", D4_RO_CONTENT_REGULAR, 0755, 0, 0, 746760,
      "2c9d712b497ee2d6c436da1dd09fb88f3a7ff535bbece9bab0e9a03c5e6cb835", NULL },
    { "usr/bin/dropbearkey", D4_RO_CONTENT_REGULAR, 0755, 0, 0, 133472,
      "3404bb0a376b7853802fa31e187b9ea60b615977c3b2dde7ed86ea181b0e7eee", NULL },
    { "usr/sbin/dropbear", D4_RO_CONTENT_REGULAR, 0755, 0, 0, 200560,
      "6fb0b5da8a4b903d075b9fd5fd735d09a58173018be83d8ab2d8f54f0e9b78c7", NULL },
    { "usr/local/bin/a90-dpublic-wifi-sta", D4_RO_CONTENT_REGULAR, 0755, 0, 0, 35289,
      "5b23ec2f6284aa3e010594307e9a0aaa064b316c171b663584232ef49bac09b9", NULL },
    { "usr/local/bin/a90-dpublic-smoke-httpd", D4_RO_CONTENT_REGULAR, 0755, 0, 0, 711136,
      "8492bf77de7293b1a42ac9b321262974045992cbc5149c8937b0a24f83fd8e56", NULL },
    { "usr/local/bin/a90-dpublic-hud-intent", D4_RO_CONTENT_REGULAR, 0755, 0, 0, 71480,
      "f09d1eb6b57de50ed14fdf17d4d77751fc86ff41782ab51c90bb40ea070334f3", NULL },
    { "usr/local/bin/a90-dpublic-hud-presenter", D4_RO_CONTENT_REGULAR, 0755, 0, 0, 71504,
      "055588a9c9ce61afa47ed532b2a7f62dbbef2a319d0b07fda1cd9b8d0fa2a76d", NULL },
    { "usr/local/bin/a90-service-launch", D4_RO_CONTENT_REGULAR, 0755, 0, 0, 1328,
      "31093fd314f1ccfb072d19678739fd92f198990171d3713194b3faacfe771912", NULL },
    { "usr/sbin/iw", D4_RO_CONTENT_REGULAR, 0755, 0, 0, 342952,
      "a244c8cc1740d8e3e92589dfd1b9527dbbfc97692cc23e8cfb96cd9d10d8d7da", NULL },
    { "lib/aarch64-linux-gnu/libselinux.so.1", D4_RO_CONTENT_REGULAR, 0644, 0, 0, 198800,
      "6f51339a6f92f88785dfcfdb13194c3d10cb10ccee1d0ddb5b3e3445145c761c", NULL },
    { "lib/aarch64-linux-gnu/libc.so.6", D4_RO_CONTENT_REGULAR, 0755, 0, 0, 1651408,
      "e4ac8ae1d81e4865e3aadedb962879cf9415903b3f2ba81ec75e9962b86ab8b0", NULL },
    { "lib/ld-linux-aarch64.so.1", D4_RO_CONTENT_SYMLINK, 0777, 0, 0, 39,
      "17538b8f9889a470c061f69a8fea8124da89627311cd16546c133a89f09056df",
      "aarch64-linux-gnu/ld-linux-aarch64.so.1" },
    { "lib/aarch64-linux-gnu/libpcre2-8.so.0", D4_RO_CONTENT_SYMLINK, 0777, 0, 0, 20,
      "cabf859fab34e77fba3ab3485878cc19014327246a7c6aa21ac0d2d1a32dcc81",
      "libpcre2-8.so.0.11.2" },
};

struct d4_userdata_target {
    char sysname[64];
    char devname[128];
    unsigned int major_num;
    unsigned int minor_num;
    unsigned long long sectors;
    unsigned long long bytes;
    int ro;
    int mounted;
    int node_exists;
    int byname_exists;
    int byname_matches;
};

static const char *const d4_forbidden_names[] = {
    "efs",
    "sec_efs",
    "modem",
    "rpmb",
    "keymaster",
    "vbmeta",
    "dsp",
    "keydata",
    "keyrefuge",
    "bootloader",
    "persist",
    "gpt",
    NULL,
};

static int d4_has_forbidden_name(const char *s) {
    int i;

    if (s == NULL) {
        return 0;
    }
    for (i = 0; d4_forbidden_names[i] != NULL; ++i) {
        if (strstr(s, d4_forbidden_names[i]) != NULL) {
            return 1;
        }
    }
    return 0;
}

static int d4_copy_value(char *dst, size_t dst_size, const char *src) {
    size_t len;

    if (dst == NULL || dst_size == 0 || src == NULL) {
        return -EINVAL;
    }
    len = strlen(src);
    while (len > 0 && (src[len - 1] == '\n' || src[len - 1] == '\r')) {
        --len;
    }
    if (len >= dst_size) {
        return -ENAMETOOLONG;
    }
    memcpy(dst, src, len);
    dst[len] = '\0';
    return 0;
}

static int d4_parse_uint(const char *s, unsigned int *out) {
    char *end = NULL;
    unsigned long value;

    if (s == NULL || out == NULL || s[0] == '\0') {
        return -EINVAL;
    }
    errno = 0;
    value = strtoul(s, &end, 10);
    if (errno != 0 || end == s || *end != '\0' || value > 0xffffffffUL) {
        return -EINVAL;
    }
    *out = (unsigned int)value;
    return 0;
}

static int d4_parse_u64(const char *s, unsigned long long *out) {
    char *end = NULL;
    unsigned long long value;

    if (s == NULL || out == NULL || s[0] == '\0') {
        return -EINVAL;
    }
    errno = 0;
    value = strtoull(s, &end, 10);
    if (errno != 0 || end == s || *end != '\0') {
        return -EINVAL;
    }
    *out = value;
    return 0;
}

static int d4_read_trimmed_file(const char *path, char *out, size_t out_size) {
    FILE *fp;
    char line[256];

    if (out == NULL || out_size == 0) {
        return -EINVAL;
    }
    fp = fopen(path, "r");
    if (fp == NULL) {
        return -errno;
    }
    if (fgets(line, sizeof(line), fp) == NULL) {
        int rc = ferror(fp) ? -errno : -EINVAL;
        fclose(fp);
        return rc;
    }
    fclose(fp);
    return d4_copy_value(out, out_size, line);
}

static int d4_join_root(char *out, size_t out_size, const char *leaf) {
    int n = snprintf(out, out_size, "%s/%s", A90_D4_ROOT, leaf);

    if (n < 0 || (size_t)n >= out_size) {
        return -ENAMETOOLONG;
    }
    return 0;
}

static int d4_source_path_clean(const char *path) {
    const char *c;
    size_t root_len;

    if (path == NULL || path[0] == '\0') {
        return 0;
    }
    root_len = strlen(A90_D4_ALLOWED_SOURCE_ROOT);
    if (strncmp(path, A90_D4_ALLOWED_SOURCE_ROOT, root_len) != 0 ||
        path[root_len] == '\0') {
        return 0;
    }
    if (strstr(path, "..") != NULL) {
        return 0;
    }
    for (c = path; *c != '\0'; ++c) {
        if (*c == '\n' || *c == '\r' || *c == '\t') {
            return 0;
        }
    }
    return 1;
}

static int d4_join_path(char *out, size_t out_size, const char *left, const char *right) {
    int n;

    if (out == NULL || out_size == 0 || left == NULL || right == NULL ||
        left[0] == '\0' || right[0] == '\0') {
        return -EINVAL;
    }
    n = snprintf(out, out_size, "%s/%s", left, right);
    if (n < 0 || (size_t)n >= out_size) {
        return -ENAMETOOLONG;
    }
    return 0;
}

static int d4_exact_dir_ok(const char *path) {
    struct stat st;

    if (path == NULL || path[0] == '\0') {
        return -EINVAL;
    }
    if (lstat(path, &st) < 0) {
        return -errno;
    }
    if (!S_ISDIR(st.st_mode)) {
        return -EINVAL;
    }
    return 0;
}

static int d4_symlink_target_ok(const char *path, const char *expected) {
    char target[PATH_MAX];
    ssize_t n;

    if (path == NULL || expected == NULL) {
        return -EINVAL;
    }
    n = readlink(path, target, sizeof(target) - 1);
    if (n < 0) {
        return -errno;
    }
    target[n] = '\0';
    if (strcmp(target, expected) != 0) {
        a90_console_printf("%s stop=bad-symlink path=%s target=%s expected=%s\r\n",
                           A90_D4_TAG, path, target, expected);
        return -EPERM;
    }
    return 0;
}

static int d4_sha256_file_matches(const char *path, const char *expected_sha, const char *label) {
    char actual[65];

    if (path == NULL || expected_sha == NULL || label == NULL) {
        return -EINVAL;
    }
    if (a90_helper_sha256_file(path, actual, sizeof(actual)) != 0) {
        a90_console_printf("%s %s_sha=compute-fail path=%s\r\n", A90_D4_TAG, label, path);
        return -EIO;
    }
    if (!d3_sha_equal_ci(actual, expected_sha)) {
        a90_console_printf("%s %s_sha=%s expected_sha_match=0 path=%s\r\n",
                           A90_D4_TAG, label, actual, path);
        return -EPERM;
    }
    a90_console_printf("%s %s_sha=%s expected_sha_match=1 path=%s\r\n",
                       A90_D4_TAG, label, actual, path);
    return 0;
}

static int d4_verify_e2fs_toolroot(void) {
    int rc;

    rc = d4_exact_dir_ok(A90_D4_E2FS_TOOLROOT);
    if (rc < 0) {
        a90_console_printf("%s e2fs-toolroot=fail stage=dir root=%s rc=%d\r\n",
                           A90_D4_TAG, A90_D4_E2FS_TOOLROOT, rc);
        return rc;
    }
    rc = d4_sha256_file_matches(A90_D4_E2FS_MKE2FS_HOST,
                                A90_D4_E2FS_MKE2FS_SHA,
                                "mke2fs");
    if (rc < 0) {
        return rc;
    }
    rc = d4_sha256_file_matches(A90_D4_E2FS_DUMPE2FS_HOST,
                                A90_D4_E2FS_DUMPE2FS_SHA,
                                "dumpe2fs");
    if (rc < 0) {
        return rc;
    }
    rc = d4_sha256_file_matches(A90_D4_E2FS_TUNE2FS_HOST,
                                A90_D4_E2FS_TUNE2FS_SHA,
                                "tune2fs");
    if (rc < 0) {
        return rc;
    }
    rc = d4_symlink_target_ok(A90_D4_E2FS_MKFS_EXT4_HOST, "mke2fs");
    if (rc < 0) {
        return rc;
    }
    a90_console_printf("%s e2fs-toolroot=ok root=%s mkfs.ext4=mke2fs\r\n",
                       A90_D4_TAG, A90_D4_E2FS_TOOLROOT);
    return 0;
}

static int d4_chroot_path_for_toolroot_file(const char *host_path,
                                            char *out,
                                            size_t out_size) {
    size_t root_len = strlen(A90_D4_E2FS_TOOLROOT);
    const char *suffix;

    if (host_path == NULL || out == NULL || out_size == 0) {
        return -EINVAL;
    }
    if (strncmp(host_path, A90_D4_E2FS_TOOLROOT, root_len) != 0 ||
        host_path[root_len] != '/') {
        a90_console_printf("%s refused=probe-path-outside-e2fs-toolroot path=%s root=%s\r\n",
                           A90_D4_TAG, host_path, A90_D4_E2FS_TOOLROOT);
        return -EPERM;
    }
    suffix = host_path + root_len;
    if (suffix[1] == '\0') {
        return -EINVAL;
    }
    if (strlen(suffix) >= out_size) {
        return -ENAMETOOLONG;
    }
    memcpy(out, suffix, strlen(suffix) + 1);
    return 0;
}

static int d4_regular_file_ok(const char *path) {
    int fd;
    struct stat st;
    int saved_errno;

    fd = open(path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) {
        saved_errno = errno;
        a90_console_printf("%s open=fail path=%s errno=%d (%s)\r\n",
                           A90_D4_TAG, path, saved_errno, strerror(saved_errno));
        return -saved_errno;
    }
    if (fstat(fd, &st) < 0) {
        saved_errno = errno;
        close(fd);
        return -saved_errno;
    }
    close(fd);
    if (!S_ISREG(st.st_mode) || st.st_size <= 0) {
        a90_console_printf("%s stop=not-regular-or-empty path=%s\r\n", A90_D4_TAG, path);
        return -EINVAL;
    }
    return 0;
}

static int d4_create_probe_file(const char *path, unsigned long long size_bytes) {
    int fd;
    int saved_errno;

    fd = open(path, O_RDWR | O_CREAT | O_TRUNC | O_CLOEXEC | O_NOFOLLOW, 0600);
    if (fd < 0) {
        saved_errno = errno;
        a90_console_printf("%s formatter-probe=create-fail path=%s errno=%d (%s)\r\n",
                           A90_D4_TAG, path, saved_errno, strerror(saved_errno));
        return -saved_errno;
    }
    if (ftruncate(fd, (off_t)size_bytes) < 0) {
        saved_errno = errno;
        close(fd);
        return -saved_errno;
    }
    if (fsync(fd) < 0) {
        saved_errno = errno;
        close(fd);
        return -saved_errno;
    }
    close(fd);
    a90_console_printf("%s formatter-probe=file-created path=%s size_bytes=%llu\r\n",
                       A90_D4_TAG, path, size_bytes);
    return 0;
}

static int d4_check_ext4_magic_phase(const char *path, const char *phase) {
    unsigned char magic[2] = { 0, 0 };
    int fd;
    int saved_errno;
    ssize_t n;

    fd = open(path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) {
        saved_errno = errno;
        return -saved_errno;
    }
    n = pread(fd, magic, sizeof(magic), A90_D4_EXT4_MAGIC_OFFSET);
    if (n < 0) {
        saved_errno = errno;
        close(fd);
        return -saved_errno;
    }
    close(fd);
    if (n != (ssize_t)sizeof(magic) || magic[0] != 0x53 || magic[1] != 0xef) {
        a90_console_printf("%s %s=bad-ext4-magic read=%zd magic=%02x%02x\r\n",
                           A90_D4_TAG, phase != NULL ? phase : "ext4-check",
                           n, magic[0], magic[1]);
        return -EINVAL;
    }
    a90_console_printf("%s %s=ext4-magic-ok magic=53ef offset=%d\r\n",
                       A90_D4_TAG, phase != NULL ? phase : "ext4-check",
                       A90_D4_EXT4_MAGIC_OFFSET);
    return 0;
}

static int d4_check_ext_has_journal(const char *path, const char *phase) {
    unsigned char raw[4] = { 0, 0, 0, 0 };
    unsigned int features;
    int fd;
    int saved_errno;
    ssize_t n;

    fd = open(path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) {
        saved_errno = errno;
        return -saved_errno;
    }
    n = pread(fd, raw, sizeof(raw), A90_D4_EXT_FEATURE_COMPAT_OFFSET);
    if (n < 0) {
        saved_errno = errno;
        close(fd);
        return -saved_errno;
    }
    close(fd);
    if (n != (ssize_t)sizeof(raw)) {
        return -EIO;
    }
    features = ((unsigned int)raw[0]) |
               ((unsigned int)raw[1] << 8) |
               ((unsigned int)raw[2] << 16) |
               ((unsigned int)raw[3] << 24);
    if ((features & A90_D4_EXT_COMPAT_HAS_JOURNAL) == 0) {
        a90_console_printf("%s %s=missing-has-journal feature_compat=0x%08x\r\n",
                           A90_D4_TAG, phase != NULL ? phase : "journal-check", features);
        return -EINVAL;
    }
    a90_console_printf("%s %s=has-journal-ok feature_compat=0x%08x has_journal=1\r\n",
                       A90_D4_TAG, phase != NULL ? phase : "journal-check", features);
    return 0;
}

static int d4_check_ext4_clean_no_recovery(const char *path,
                                            const char *phase) {
    unsigned char state_raw[2] = { 0, 0 };
    unsigned char incompat_raw[4] = { 0, 0, 0, 0 };
    unsigned int state;
    unsigned int incompat;
    int fd;
    int saved_errno;
    ssize_t n;

    fd = open(path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) {
        return -errno;
    }
    n = pread(fd, state_raw, sizeof(state_raw), A90_D4_EXT_STATE_OFFSET);
    if (n != (ssize_t)sizeof(state_raw)) {
        saved_errno = n < 0 ? errno : EIO;
        close(fd);
        return -saved_errno;
    }
    n = pread(fd,
              incompat_raw,
              sizeof(incompat_raw),
              A90_D4_EXT_FEATURE_INCOMPAT_OFFSET);
    if (n != (ssize_t)sizeof(incompat_raw)) {
        saved_errno = n < 0 ? errno : EIO;
        close(fd);
        return -saved_errno;
    }
    if (close(fd) < 0) {
        return -errno;
    }
    state = ((unsigned int)state_raw[0]) |
            ((unsigned int)state_raw[1] << 8);
    incompat = ((unsigned int)incompat_raw[0]) |
               ((unsigned int)incompat_raw[1] << 8) |
               ((unsigned int)incompat_raw[2] << 16) |
               ((unsigned int)incompat_raw[3] << 24);
    if (state != A90_D4_EXT_VALID_FS ||
        (incompat & A90_D4_EXT_INCOMPAT_RECOVER) != 0U) {
        a90_console_printf(
            "%s %s=unclean-or-needs-recovery state=0x%04x "
            "feature_incompat=0x%08x stop=refused\r\n",
            A90_D4_TAG,
            phase != NULL ? phase : "clean-state-check",
            state,
            incompat);
        return -EUCLEAN;
    }
    a90_console_printf(
        "%s %s=clean-no-recovery state=0x%04x feature_incompat=0x%08x\r\n",
        A90_D4_TAG,
        phase != NULL ? phase : "clean-state-check",
        state,
        incompat);
    return 0;
}

static int d4_check_ext4_label(const char *path,
                               const char *expected_label,
                               const char *phase) {
    unsigned char observed[A90_D4_EXT_LABEL_BYTES];
    unsigned char expected[A90_D4_EXT_LABEL_BYTES];
    size_t expected_size;
    int fd;
    int saved_errno;
    ssize_t n;

    if (expected_label == NULL) {
        return -EINVAL;
    }
    expected_size = strlen(expected_label);
    if (expected_size == 0 || expected_size > sizeof(expected)) {
        return -EINVAL;
    }
    memset(expected, 0, sizeof(expected));
    memcpy(expected, expected_label, expected_size);
    fd = open(path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) {
        return -errno;
    }
    n = pread(fd, observed, sizeof(observed), A90_D4_EXT_LABEL_OFFSET);
    if (n < 0) {
        saved_errno = errno;
        close(fd);
        return -saved_errno;
    }
    if (close(fd) < 0) {
        return -errno;
    }
    if (n != (ssize_t)sizeof(observed) ||
        memcmp(observed, expected, sizeof(observed)) != 0) {
        a90_console_printf("%s %s=label-mismatch expected=%s\r\n",
                           A90_D4_TAG,
                           phase != NULL ? phase : "label-check",
                           expected_label);
        return -EPERM;
    }
    a90_console_printf("%s %s=label-ok label=%s\r\n",
                       A90_D4_TAG,
                       phase != NULL ? phase : "label-check",
                       expected_label);
    return 0;
}

static int d4_uuid_hex_nibble(char value) {
    if (value >= '0' && value <= '9') {
        return value - '0';
    }
    if (value >= 'a' && value <= 'f') {
        return value - 'a' + 10;
    }
    return -1;
}

static int d4_parse_uuid(const char *value,
                         unsigned char out[A90_D4_EXT_UUID_BYTES]) {
    size_t input = 0;
    size_t output = 0;

    if (value == NULL || strlen(value) != 36U) {
        return -EINVAL;
    }
    while (input < 36U) {
        int high;
        int low;

        if (input == 8U || input == 13U || input == 18U || input == 23U) {
            if (value[input++] != '-') {
                return -EINVAL;
            }
            continue;
        }
        if (input + 1U >= 36U || output >= A90_D4_EXT_UUID_BYTES) {
            return -EINVAL;
        }
        high = d4_uuid_hex_nibble(value[input]);
        low = d4_uuid_hex_nibble(value[input + 1U]);
        if (high < 0 || low < 0) {
            return -EINVAL;
        }
        out[output++] = (unsigned char)((high << 4) | low);
        input += 2U;
    }
    return output == A90_D4_EXT_UUID_BYTES ? 0 : -EINVAL;
}

static int d4_check_ext4_uuid(const char *path,
                              const char *expected_uuid,
                              const char *phase) {
    unsigned char observed[A90_D4_EXT_UUID_BYTES];
    unsigned char expected[A90_D4_EXT_UUID_BYTES];
    int fd;
    int saved_errno;
    ssize_t n;

    if (d4_parse_uuid(expected_uuid, expected) < 0) {
        return -EINVAL;
    }
    fd = open(path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) {
        return -errno;
    }
    n = pread(fd, observed, sizeof(observed), A90_D4_EXT_UUID_OFFSET);
    if (n != (ssize_t)sizeof(observed)) {
        saved_errno = n < 0 ? errno : EIO;
        close(fd);
        return -saved_errno;
    }
    if (close(fd) < 0) {
        return -errno;
    }
    if (memcmp(observed, expected, sizeof(observed)) != 0) {
        a90_console_printf("%s %s=uuid-mismatch stop=refused\r\n",
                           A90_D4_TAG,
                           phase != NULL ? phase : "uuid-check");
        return -EPERM;
    }
    a90_console_printf("%s %s=uuid-ok uuid=%s\r\n",
                       A90_D4_TAG,
                       phase != NULL ? phase : "uuid-check",
                       expected_uuid);
    return 0;
}

static int d4_marker_clean(const char *value) {
    const char *c;

    if (value == NULL || value[0] == '\0') {
        return 0;
    }
    for (c = value; *c != '\0'; ++c) {
        if (*c == '\n' || *c == '\r' || *c == '\t' || *c == '/') {
            return 0;
        }
    }
    return 1;
}

static int d4_run_busybox(char *const argv[], int timeout_ms) {
    struct a90_run_config config;
    struct a90_run_result result;
    pid_t pid = -1;
    int rc;

    memset(&config, 0, sizeof(config));
    config.tag = "server-distro-d4";
    config.argv = argv;
    config.stdio_mode = A90_RUN_STDIO_CONSOLE;
    config.timeout_ms = timeout_ms;
    config.stop_timeout_ms = 2000;

    rc = a90_run_spawn(&config, &pid);
    if (rc < 0) {
        return rc;
    }
    rc = a90_run_wait(pid, &config, &result);
    if (rc < 0) {
        return rc;
    }
    return a90_run_result_to_rc(&result);
}

static int d4_run_e2fs_chroot(char *const chroot_argv[], int timeout_ms) {
    char *argv[12];
    size_t count = 0;
    size_t i = 0;

    if (chroot_argv == NULL || chroot_argv[0] == NULL) {
        return -EINVAL;
    }
    argv[count++] = (char *)A90_D4_BUSYBOX;
    argv[count++] = (char *)"chroot";
    argv[count++] = (char *)A90_D4_E2FS_TOOLROOT;
    while (chroot_argv[i] != NULL) {
        if (count + 1 >= sizeof(argv) / sizeof(argv[0])) {
            return -E2BIG;
        }
        argv[count++] = chroot_argv[i++];
    }
    argv[count] = NULL;
    return d4_run_busybox(argv, timeout_ms);
}

static int d4_run_e2fs_mkfs_ext4(const char *label,
                                 const char *chroot_target,
                                 const char *phase) {
    char *mkfs_argv[] = {
        (char *)A90_D4_E2FS_MKFS_EXT4_CHROOT,
        (char *)"-F",
        (char *)"-L",
        NULL,
        NULL,
        NULL,
    };
    int rc;

    if (label == NULL || chroot_target == NULL) {
        return -EINVAL;
    }
    mkfs_argv[3] = (char *)label;
    mkfs_argv[4] = (char *)chroot_target;
    a90_console_printf("%s %s=begin formatter=e2fsprogs-mkfs.ext4 target=%s label=%s root=%s\r\n",
                       A90_D4_TAG, phase != NULL ? phase : "mkfs", chroot_target,
                       label, A90_D4_E2FS_TOOLROOT);
    rc = d4_run_e2fs_chroot(mkfs_argv, A90_D4_FORMAT_TIMEOUT_MS);
    if (rc != 0) {
        a90_console_printf("%s %s=fail formatter=e2fsprogs-mkfs.ext4 rc=%d\r\n",
                           A90_D4_TAG, phase != NULL ? phase : "mkfs", rc);
        return rc > 0 ? -EIO : rc;
    }
    return 0;
}

static int d4_run_e2fs_dumpe2fs_header(const char *chroot_target, const char *phase) {
    char *dump_argv[] = {
        (char *)A90_D4_E2FS_DUMPE2FS_CHROOT,
        (char *)"-h",
        NULL,
        NULL,
    };
    int rc;

    if (chroot_target == NULL) {
        return -EINVAL;
    }
    dump_argv[2] = (char *)chroot_target;
    a90_console_printf("%s %s=dumpe2fs-header-begin target=%s\r\n",
                       A90_D4_TAG, phase != NULL ? phase : "journal-check", chroot_target);
    rc = d4_run_e2fs_chroot(dump_argv, A90_D4_FORMAT_TIMEOUT_MS);
    if (rc != 0) {
        a90_console_printf("%s %s=dumpe2fs-header-fail rc=%d\r\n",
                           A90_D4_TAG, phase != NULL ? phase : "journal-check", rc);
        return rc > 0 ? -EIO : rc;
    }
    a90_console_printf("%s %s=dumpe2fs-header-ok\r\n",
                       A90_D4_TAG, phase != NULL ? phase : "journal-check");
    return 0;
}

static int d4_parse_uevent(const char *path,
                           struct d4_userdata_target *target,
                           int *is_userdata_out) {
    FILE *fp;
    char line[256];
    char partname[128] = "";
    int saw_devname = 0;
    int saw_major = 0;
    int saw_minor = 0;

    if (target == NULL || is_userdata_out == NULL) {
        return -EINVAL;
    }
    *is_userdata_out = 0;
    fp = fopen(path, "r");
    if (fp == NULL) {
        return -errno;
    }
    while (fgets(line, sizeof(line), fp) != NULL) {
        if (strncmp(line, "DEVNAME=", 8) == 0) {
            if (d4_copy_value(target->devname, sizeof(target->devname), line + 8) < 0) {
                fclose(fp);
                return -EINVAL;
            }
            saw_devname = 1;
        } else if (strncmp(line, "MAJOR=", 6) == 0) {
            char value[32];
            if (d4_copy_value(value, sizeof(value), line + 6) < 0 ||
                d4_parse_uint(value, &target->major_num) < 0) {
                fclose(fp);
                return -EINVAL;
            }
            saw_major = 1;
        } else if (strncmp(line, "MINOR=", 6) == 0) {
            char value[32];
            if (d4_copy_value(value, sizeof(value), line + 6) < 0 ||
                d4_parse_uint(value, &target->minor_num) < 0) {
                fclose(fp);
                return -EINVAL;
            }
            saw_minor = 1;
        } else if (strncmp(line, "PARTNAME=", 9) == 0) {
            if (d4_copy_value(partname, sizeof(partname), line + 9) < 0) {
                fclose(fp);
                return -EINVAL;
            }
        }
    }
    if (ferror(fp)) {
        int rc = -errno;
        fclose(fp);
        return rc;
    }
    fclose(fp);
    if (strcmp(partname, A90_D4_EXPECTED_PARTNAME) != 0) {
        return 0;
    }
    if (!saw_devname || !saw_major || !saw_minor) {
        return -EINVAL;
    }
    *is_userdata_out = 1;
    return 0;
}

static int d4_read_target_shape(struct d4_userdata_target *target) {
    char path[PATH_MAX];
    char value[64];
    unsigned long long sectors;
    unsigned int ro_value;
    int n;
    int rc;

    n = snprintf(path, sizeof(path), "/sys/class/block/%s/size", target->sysname);
    if (n < 0 || (size_t)n >= sizeof(path)) {
        return -ENAMETOOLONG;
    }
    rc = d4_read_trimmed_file(path, value, sizeof(value));
    if (rc < 0) {
        return rc;
    }
    rc = d4_parse_u64(value, &sectors);
    if (rc < 0) {
        return rc;
    }
    n = snprintf(path, sizeof(path), "/sys/class/block/%s/ro", target->sysname);
    if (n < 0 || (size_t)n >= sizeof(path)) {
        return -ENAMETOOLONG;
    }
    rc = d4_read_trimmed_file(path, value, sizeof(value));
    if (rc < 0) {
        return rc;
    }
    rc = d4_parse_uint(value, &ro_value);
    if (rc < 0) {
        return rc;
    }
    if (sectors > 0xffffffffffffffffULL / 512ULL) {
        return -EOVERFLOW;
    }
    target->sectors = sectors;
    target->bytes = sectors * 512ULL;
    target->ro = ro_value != 0;
    return 0;
}

static int d4_block_node_matches(const char *path, const struct d4_userdata_target *target, int *matches_out) {
    struct stat st;
    dev_t wanted;

    if (matches_out == NULL || target == NULL) {
        return -EINVAL;
    }
    *matches_out = 0;
    if (stat(path, &st) < 0) {
        return -errno;
    }
    wanted = makedev(target->major_num, target->minor_num);
    if (S_ISBLK(st.st_mode) && st.st_rdev == wanted) {
        *matches_out = 1;
    }
    return 0;
}

static int d4_path_mounted_as_target(const char *source,
                                     const char *mountpoint,
                                     const struct d4_userdata_target *target) {
    int matches = 0;

    if (strcmp(mountpoint, A90_D4_ROOT) == 0) {
        return 1;
    }
    if (strcmp(source, A90_D4_NODE) == 0) {
        return 1;
    }
    if (source[0] == '/' && d4_block_node_matches(source, target, &matches) == 0 && matches) {
        return 1;
    }
    return 0;
}

static int d4_target_is_mounted(const struct d4_userdata_target *target) {
    FILE *fp;
    char source[PATH_MAX];
    char mountpoint[PATH_MAX];
    char fstype[64];
    int mounted = 0;

    if (target == NULL) {
        return -EINVAL;
    }
    fp = fopen("/proc/mounts", "r");
    if (fp == NULL) {
        return -errno;
    }
    while (fscanf(fp, "%1023s %1023s %63s %*s %*d %*d\n", source, mountpoint, fstype) == 3) {
        (void)fstype;
        if (d4_path_mounted_as_target(source, mountpoint, target)) {
            mounted = 1;
            break;
        }
    }
    fclose(fp);
    return mounted;
}

static int d4_check_optional_byname(struct d4_userdata_target *target) {
    struct stat st;
    int rc;
    int matches = 0;

    target->byname_exists = 0;
    target->byname_matches = 0;
    rc = lstat("/dev/block/by-name/userdata", &st);
    if (rc < 0) {
        return errno == ENOENT ? 0 : -errno;
    }
    target->byname_exists = 1;
    rc = d4_block_node_matches("/dev/block/by-name/userdata", target, &matches);
    if (rc < 0) {
        return rc;
    }
    target->byname_matches = matches;
    return matches ? 0 : -EPERM;
}

static int d4_check_private_node(struct d4_userdata_target *target) {
    struct stat st;
    dev_t wanted = makedev(target->major_num, target->minor_num);

    target->node_exists = 0;
    if (lstat(A90_D4_NODE, &st) < 0) {
        return errno == ENOENT ? 0 : -errno;
    }
    target->node_exists = 1;
    if (!S_ISBLK(st.st_mode) || st.st_rdev != wanted) {
        return -EPERM;
    }
    return 0;
}

static int d4_resolve_userdata(struct d4_userdata_target *target) {
    DIR *dir;
    struct dirent *entry;
    struct d4_userdata_target found;
    int found_count = 0;
    int rc = 0;

    if (target == NULL) {
        return -EINVAL;
    }
    memset(target, 0, sizeof(*target));
    memset(&found, 0, sizeof(found));
    dir = opendir("/sys/class/block");
    if (dir == NULL) {
        return -errno;
    }
    while ((entry = readdir(dir)) != NULL) {
        char uevent_path[PATH_MAX];
        struct d4_userdata_target candidate;
        int is_userdata = 0;
        int n;

        if (entry->d_name[0] == '.') {
            continue;
        }
        memset(&candidate, 0, sizeof(candidate));
        if (d4_copy_value(candidate.sysname, sizeof(candidate.sysname), entry->d_name) < 0) {
            rc = -EINVAL;
            break;
        }
        n = snprintf(uevent_path, sizeof(uevent_path),
                     "/sys/class/block/%s/uevent", entry->d_name);
        if (n < 0 || (size_t)n >= sizeof(uevent_path)) {
            rc = -ENAMETOOLONG;
            break;
        }
        rc = d4_parse_uevent(uevent_path, &candidate, &is_userdata);
        if (rc < 0) {
            break;
        }
        if (!is_userdata) {
            continue;
        }
        ++found_count;
        if (found_count == 1) {
            found = candidate;
        }
    }
    closedir(dir);
    if (rc < 0) {
        return rc;
    }
    if (found_count != 1) {
        a90_console_printf("%s stop=userdata-partname-count count=%d\r\n", A90_D4_TAG, found_count);
        return -ENOENT;
    }
    rc = d4_read_target_shape(&found);
    if (rc < 0) {
        return rc;
    }
    if (found.ro) {
        a90_console_printf("%s stop=target-readonly devname=%s\r\n", A90_D4_TAG, found.devname);
        return -EROFS;
    }
    if (found.bytes < A90_D4_MIN_BYTES || found.bytes > A90_D4_MAX_BYTES) {
        a90_console_printf("%s stop=size-out-of-range bytes=%llu\r\n", A90_D4_TAG, found.bytes);
        return -ERANGE;
    }
    if (d4_has_forbidden_name(found.sysname) || d4_has_forbidden_name(found.devname)) {
        a90_console_printf("%s stop=forbidden-name devname=%s sysname=%s\r\n",
                           A90_D4_TAG, found.devname, found.sysname);
        return -EPERM;
    }
    rc = d4_check_optional_byname(&found);
    if (rc < 0) {
        a90_console_printf("%s stop=byname-mismatch-or-broken rc=%d\r\n", A90_D4_TAG, rc);
        return rc;
    }
    rc = d4_check_private_node(&found);
    if (rc < 0) {
        a90_console_printf("%s stop=private-node-mismatch node=%s rc=%d\r\n",
                           A90_D4_TAG, A90_D4_NODE, rc);
        return rc;
    }
    rc = d4_target_is_mounted(&found);
    if (rc < 0) {
        return rc;
    }
    found.mounted = rc;
    *target = found;
    return 0;
}

static void d4_print_target(const struct d4_userdata_target *target, const char *phase) {
    a90_console_printf(
        "%s %s target.source=partname-scan target.devname=%s target.sysname=%s "
        "target.dev=%u:%u target.sectors=%llu target.size_bytes=%llu "
        "target.ro=%d target.mounted=%d target.node=%s target.node_exists=%d "
        "target.byname_exists=%d target.byname_matches=%d\r\n",
        A90_D4_TAG,
        phase,
        target->devname,
        target->sysname,
        target->major_num,
        target->minor_num,
        target->sectors,
        target->bytes,
        target->ro,
        target->mounted,
        A90_D4_NODE,
        target->node_exists,
        target->byname_exists,
        target->byname_matches);
}

static int d4_parse_expected_dev(const char *s, unsigned int *major_out, unsigned int *minor_out) {
    char *end = NULL;
    unsigned long major_value;
    unsigned long minor_value;

    if (s == NULL || major_out == NULL || minor_out == NULL) {
        return -EINVAL;
    }
    errno = 0;
    major_value = strtoul(s, &end, 10);
    if (errno != 0 || end == s || *end != ':' || major_value > 0xffffffffUL) {
        return -EINVAL;
    }
    ++end;
    errno = 0;
    minor_value = strtoul(end, &end, 10);
    if (errno != 0 || *end != '\0' || minor_value > 0xffffffffUL) {
        return -EINVAL;
    }
    *major_out = (unsigned int)major_value;
    *minor_out = (unsigned int)minor_value;
    return 0;
}

static int d4_compare_expected(const struct d4_userdata_target *target,
                               const char *expected_devname,
                               const char *expected_dev,
                               const char *expected_sectors) {
    unsigned int expected_major = 0;
    unsigned int expected_minor = 0;
    unsigned long long sectors = 0;
    int rc;

    rc = d4_parse_expected_dev(expected_dev, &expected_major, &expected_minor);
    if (rc < 0) {
        return rc;
    }
    rc = d4_parse_u64(expected_sectors, &sectors);
    if (rc < 0) {
        return rc;
    }
    if (strcmp(target->devname, expected_devname) != 0 ||
        target->major_num != expected_major ||
        target->minor_num != expected_minor ||
        target->sectors != sectors) {
        a90_console_printf("%s stop=expected-identity-mismatch expected_devname=%s "
                           "expected_dev=%s expected_sectors=%s\r\n",
                           A90_D4_TAG, expected_devname, expected_dev, expected_sectors);
        d4_print_target(target, "actual");
        return -EPERM;
    }
    return 0;
}

static int d4_compare_ro_expected(const struct d4_userdata_target *target,
                                  const char *expected_devname,
                                  const char *expected_devt_binding,
                                  const char *expected_sectors) {
#if A90_AUTO_HANDOFF_USERDATA_DYNAMIC_DEVT
    unsigned long long sectors = 0;

    if (target == NULL || expected_devname == NULL ||
        expected_devt_binding == NULL || expected_sectors == NULL ||
        strcmp(expected_devt_binding,
               "runtime-resolved-same-session") != 0 ||
        d4_parse_u64(expected_sectors, &sectors) < 0) {
        return -EINVAL;
    }
    if (strcmp(target->devname, expected_devname) != 0 ||
        target->sectors != sectors) {
        a90_console_printf(
            "%s stop=expected-stable-identity-mismatch "
            "expected_devname=%s expected_sectors=%s devt_policy=%s\r\n",
            A90_D4_TAG,
            expected_devname,
            expected_sectors,
            expected_devt_binding);
        d4_print_target(target, "actual");
        return -EPERM;
    }
    return 0;
#else
    return d4_compare_expected(target,
                               expected_devname,
                               expected_devt_binding,
                               expected_sectors);
#endif
}

static int d4_ensure_userdata_node(const struct d4_userdata_target *target) {
    struct stat st;
    dev_t wanted = makedev(target->major_num, target->minor_num);
    int rc;

    rc = d3_mkdir_p("/dev/block", 0755);
    if (rc < 0) {
        return rc;
    }
    if (lstat(A90_D4_NODE, &st) == 0) {
        if (S_ISBLK(st.st_mode) && st.st_rdev == wanted) {
            (void)chmod(A90_D4_NODE, 0600);
            a90_console_printf("%s node=exists-ok path=%s dev=%u:%u\r\n",
                               A90_D4_TAG, A90_D4_NODE,
                               target->major_num, target->minor_num);
            return 0;
        }
        a90_console_printf("%s stop=node-exists-wrong path=%s\r\n", A90_D4_TAG, A90_D4_NODE);
        return -EPERM;
    }
    if (errno != ENOENT) {
        return -errno;
    }
    if (mknod(A90_D4_NODE, S_IFBLK | 0600, wanted) < 0) {
        return -errno;
    }
    a90_console_printf("%s node=created path=%s dev=%u:%u\r\n",
                       A90_D4_TAG, A90_D4_NODE,
                       target->major_num, target->minor_num);
    return 0;
}

static int d4_ensure_toolroot_userdata_node(const struct d4_userdata_target *target) {
    char dev_dir[PATH_MAX];
    char node_path[PATH_MAX];
    struct stat st;
    dev_t wanted;
    int rc;

    if (target == NULL) {
        return -EINVAL;
    }
    rc = d4_join_path(dev_dir, sizeof(dev_dir), A90_D4_E2FS_TOOLROOT, "dev/block");
    if (rc < 0) {
        return rc;
    }
    rc = d4_join_path(node_path, sizeof(node_path), A90_D4_E2FS_TOOLROOT, "dev/block/a90-userdata");
    if (rc < 0) {
        return rc;
    }
    rc = d3_mkdir_p(dev_dir, 0755);
    if (rc < 0) {
        return rc;
    }
    wanted = makedev(target->major_num, target->minor_num);
    if (lstat(node_path, &st) == 0) {
        if (S_ISBLK(st.st_mode) && st.st_rdev == wanted) {
            (void)chmod(node_path, 0600);
            a90_console_printf("%s e2fs-toolroot-node=exists-ok path=%s dev=%u:%u\r\n",
                               A90_D4_TAG, node_path,
                               target->major_num, target->minor_num);
            return 0;
        }
        a90_console_printf("%s stop=e2fs-toolroot-node-exists-wrong path=%s\r\n",
                           A90_D4_TAG, node_path);
        return -EPERM;
    }
    if (errno != ENOENT) {
        return -errno;
    }
    if (mknod(node_path, S_IFBLK | 0600, wanted) < 0) {
        return -errno;
    }
    a90_console_printf("%s e2fs-toolroot-node=created path=%s dev=%u:%u\r\n",
                       A90_D4_TAG, node_path,
                       target->major_num, target->minor_num);
    return 0;
}

static int d4_mount_userdata_root(void) {
    char *const argv[] = {
        (char *)A90_D4_BUSYBOX,
        (char *)"mount",
        (char *)"-t",
        (char *)"ext4",
        (char *)"-o",
        (char *)"rw",
        (char *)A90_D4_NODE,
        (char *)A90_D4_ROOT,
        NULL,
    };
    int mounted;
    int rc;

    rc = d3_mkdir_p(A90_D4_ROOT, 0755);
    if (rc < 0) {
        return rc;
    }
    mounted = d3_path_is_mounted(A90_D4_ROOT);
    if (mounted < 0) {
        return mounted;
    }
    if (mounted) {
        a90_console_printf("%s rootfs=already-mounted root=%s\r\n", A90_D4_TAG, A90_D4_ROOT);
        return 0;
    }
    rc = d4_run_busybox(argv, A90_D4_SWITCH_TIMEOUT_MS);
    if (rc != 0) {
        a90_console_printf("%s mount=fail rc=%d root=%s node=%s\r\n",
                           A90_D4_TAG, rc, A90_D4_ROOT, A90_D4_NODE);
        return rc > 0 ? -EIO : rc;
    }
    a90_console_printf("%s rootfs=mounted root=%s node=%s\r\n",
                       A90_D4_TAG, A90_D4_ROOT, A90_D4_NODE);
    return 0;
}

static int d4_check_userdata_init(void) {
    char init_path[PATH_MAX];
    struct stat st;
    int rc = d4_join_root(init_path, sizeof(init_path), "sbin/init");

    if (rc < 0) {
        return rc;
    }
    if (stat(init_path, &st) < 0) {
        return -errno;
    }
    if (!S_ISREG(st.st_mode) || (st.st_mode & 0111) == 0) {
        return -EINVAL;
    }
    a90_console_printf("%s appliance_init=ok path=%s mode=%o\r\n",
                       A90_D4_TAG, init_path, (unsigned int)(st.st_mode & 0777));
    return 0;
}

static int d4_write_marker(void) {
    char marker_path[PATH_MAX];
    const char payload[] = A90_D4_MARKER_VALUE "\n";
    int fd;
    int rc;

    rc = d4_join_root(marker_path, sizeof(marker_path), A90_D4_MARKER_LEAF);
    if (rc < 0) {
        return rc;
    }
    fd = open(marker_path, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC, 0644);
    if (fd < 0) {
        return -errno;
    }
    if (write(fd, payload, sizeof(payload) - 1) != (ssize_t)(sizeof(payload) - 1)) {
        rc = -errno;
        close(fd);
        return rc == 0 ? -EIO : rc;
    }
    if (fsync(fd) < 0) {
        rc = -errno;
        close(fd);
        return rc;
    }
    close(fd);
    a90_console_printf("%s marker=written path=%s value=%s\r\n",
                       A90_D4_TAG, marker_path, A90_D4_MARKER_VALUE);
    return 0;
}

static int d4_read_marker(char *out, size_t out_size) {
    char marker_path[PATH_MAX];
    int rc = d4_join_root(marker_path, sizeof(marker_path), A90_D4_MARKER_LEAF);

    if (rc < 0) {
        return rc;
    }
    return d4_read_trimmed_file(marker_path, out, out_size);
}

static int d4_userdata_ro_expected_values_valid(const char *expected_devname,
                                                const char *expected_devt_binding,
                                                const char *expected_sectors,
                                                const char *expected_label,
                                                const char *expected_marker,
                                                const char *expected_uuid,
                                                const char *expected_content_manifest_sha256) {
    unsigned long long sectors = 0;

    if (expected_devname == NULL || strcmp(expected_devname, "sda33") != 0 ||
        d4_parse_u64(expected_sectors, &sectors) < 0 ||
        strcmp(expected_label != NULL ? expected_label : "", "A90D4ROOT") != 0 ||
        strcmp(expected_marker != NULL ? expected_marker : "",
               A90_D4_MARKER_VALUE) != 0 ||
        strcmp(expected_uuid != NULL ? expected_uuid : "",
               A90_D4_H14_UUID) != 0 ||
        strcmp(expected_content_manifest_sha256 != NULL
                   ? expected_content_manifest_sha256
                   : "",
               A90_D4_H14_CONTENT_MANIFEST_SHA256) != 0) {
        return -EINVAL;
    }
#if A90_AUTO_HANDOFF_USERDATA_DYNAMIC_DEVT
    if (expected_devt_binding == NULL ||
        strcmp(expected_devt_binding,
               "runtime-resolved-same-session") != 0) {
        return -EINVAL;
    }
#else
    {
        unsigned int major_num = 0;
        unsigned int minor_num = 0;

        if (d4_parse_expected_dev(expected_devt_binding,
                                  &major_num,
                                  &minor_num) < 0) {
            return -EINVAL;
        }
        if (major_num != 259U || minor_num != 17U) {
            return -EPERM;
        }
    }
#endif
    if (sectors != 231577432ULL) {
        return -EPERM;
    }
    return 0;
}

static int d4_userdata_ro_static_preflight(
    const char *expected_devname,
    const char *expected_devt_binding,
    const char *expected_sectors,
    const char *expected_label,
    const char *expected_uuid,
    const char *phase,
    struct d4_userdata_target *target_out) {
    struct d4_userdata_target target;
    int rc;

    if (target_out == NULL) {
        return -EINVAL;
    }
    rc = d4_resolve_userdata(&target);
    if (rc < 0) {
        return rc;
    }
    d4_print_target(&target, phase);
    rc = d4_compare_ro_expected(&target,
                                expected_devname,
                                expected_devt_binding,
                                expected_sectors);
    if (rc < 0) {
        return rc;
    }
    if (target.mounted) {
        a90_console_printf("%s stop=userdata-already-mounted phase=%s\r\n",
                           A90_D4_TAG,
                           phase != NULL ? phase : "read-only-preflight");
        return -EBUSY;
    }
    rc = d4_ensure_userdata_node(&target);
    if (rc < 0) {
        return rc;
    }
    rc = d4_check_ext4_magic_phase(A90_D4_NODE, phase);
    if (rc < 0) {
        return rc;
    }
    rc = d4_check_ext_has_journal(A90_D4_NODE, phase);
    if (rc < 0) {
        return rc;
    }
    rc = d4_check_ext4_clean_no_recovery(A90_D4_NODE, phase);
    if (rc < 0) {
        return rc;
    }
    rc = d4_check_ext4_label(A90_D4_NODE, expected_label, phase);
    if (rc < 0) {
        return rc;
    }
    rc = d4_check_ext4_uuid(A90_D4_NODE, expected_uuid, phase);
    if (rc < 0) {
        return rc;
    }
    *target_out = target;
    return 0;
}

static int d4_mount_userdata_readonly_no_replay(void) {
    struct statvfs fs;
    int mounted;
    int rc;

    rc = d3_mkdir_p(A90_D3_ROOT, 0755);
    if (rc < 0) {
        return rc;
    }
    mounted = d3_path_is_mounted(A90_D3_ROOT);
    if (mounted < 0) {
        return mounted;
    }
    if (mounted) {
        a90_console_printf("%s stop=root-already-mounted root=%s\r\n",
                           A90_D4_TAG,
                           A90_D3_ROOT);
        return -EBUSY;
    }
    if (mount(A90_D4_NODE,
              A90_D3_ROOT,
              "ext4",
              MS_RDONLY | MS_NOSUID | MS_NODEV,
              "noload") < 0) {
        rc = -errno;
        a90_console_printf("%s rootfs=mount-ro-noload-fail root=%s rc=%d\r\n",
                           A90_D4_TAG,
                           A90_D3_ROOT,
                           rc);
        return rc;
    }
    if (statvfs(A90_D3_ROOT, &fs) < 0 || (fs.f_flag & ST_RDONLY) == 0) {
        rc = errno != 0 ? -errno : -EPERM;
        (void)umount2(A90_D3_ROOT, MNT_DETACH);
        a90_console_printf("%s rootfs=read-only-proof-fail root=%s rc=%d\r\n",
                           A90_D4_TAG,
                           A90_D3_ROOT,
                           rc);
        return rc;
    }
    a90_console_printf(
        "%s rootfs=mounted-ro-noload root=%s node=%s userdata_write=0\r\n",
        A90_D4_TAG,
        A90_D3_ROOT,
        A90_D4_NODE);
    return 0;
}

static int d4_userdata_ro_check_marker(const char *expected_marker) {
    char path[PATH_MAX];
    char content[128];
    char expected[128];
    struct stat before;
    struct stat opened;
    size_t expected_size;
    ssize_t count;
    ssize_t extra;
    int fd;
    int rc;

    if (expected_marker == NULL ||
        strcmp(expected_marker, A90_D4_MARKER_VALUE) != 0) {
        return -EINVAL;
    }
    expected_size = strlen(expected_marker) + 1U;
    if (expected_size >= sizeof(expected)) {
        return -EOVERFLOW;
    }
    rc = d3_join(path, sizeof(path), A90_D3_ROOT, A90_D4_MARKER_LEAF);
    if (rc < 0) {
        return rc;
    }
    if (lstat(path, &before) < 0 ||
        !S_ISREG(before.st_mode) ||
        S_ISLNK(before.st_mode) ||
        before.st_uid != 0 ||
        before.st_gid != 0 ||
        before.st_nlink != 1 ||
        (before.st_mode & 0022) != 0 ||
        before.st_size != (off_t)expected_size) {
        return -EPERM;
    }
    fd = open(path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) {
        return -errno;
    }
    if (fstat(fd, &opened) < 0 ||
        opened.st_dev != before.st_dev ||
        opened.st_ino != before.st_ino ||
        opened.st_size != before.st_size) {
        int saved_errno = errno != 0 ? errno : ESTALE;

        close(fd);
        return -saved_errno;
    }
    count = read(fd, content, sizeof(content) - 1U);
    extra = count >= 0 ? read(fd, content + count, 1U) : -1;
    if (close(fd) < 0 && count >= 0 && extra == 0) {
        return -errno;
    }
    if (count != (ssize_t)expected_size || extra != 0) {
        return count < 0 ? -errno : -EOVERFLOW;
    }
    memcpy(expected, expected_marker, expected_size - 1U);
    expected[expected_size - 1U] = '\n';
    if (memcmp(content, expected, expected_size) != 0) {
        return -EPERM;
    }
    a90_console_printf("%s appliance_marker=ok value=%s immutable=1\r\n",
                       A90_D4_TAG,
                       expected_marker);
    return 0;
}

static int d4_userdata_ro_hash_fd(int fd,
                                  off_t expected_size,
                                  const char *expected_sha256) {
    static const char hex[] = "0123456789abcdef";
    unsigned char buffer[32768];
    struct a90_sha256_ctx context;
    unsigned char digest[32];
    char actual[65];
    off_t offset = 0;
    unsigned int index;

    if (fd < 0 || expected_size <= 0 ||
        expected_size > 64LL * 1024LL * 1024LL || expected_sha256 == NULL ||
        strlen(expected_sha256) != 64U) {
        return -EINVAL;
    }
    a90_helper_sha256_init(&context);
    while (offset < expected_size) {
        size_t want = (size_t)(expected_size - offset);
        ssize_t got;

        if (want > sizeof(buffer)) {
            want = sizeof(buffer);
        }
        got = pread(fd, buffer, want, offset);
        if (got < 0) {
            if (errno == EINTR) {
                continue;
            }
            return -errno;
        }
        if (got == 0) {
            return -ESTALE;
        }
        a90_helper_sha256_update(&context, buffer, (size_t)got);
        offset += got;
    }
    if (pread(fd, buffer, 1U, expected_size) != 0) {
        return -ESTALE;
    }
    a90_helper_sha256_final(&context, digest);
    for (index = 0; index < sizeof(digest); ++index) {
        actual[index * 2U] = hex[digest[index] >> 4U];
        actual[index * 2U + 1U] = hex[digest[index] & 0x0fU];
    }
    actual[64] = '\0';
    return d3_sha_equal_ci(actual, expected_sha256) ? 0 : -ESTALE;
}

static int d4_userdata_ro_check_content_one(
    const struct d4_ro_content_identity *expected) {
    char path[PATH_MAX];
    char target[PATH_MAX];
    struct stat before;
    struct stat after;
    struct stat opened;
    struct stat opened_after;
    int open_flags = O_RDONLY | O_CLOEXEC;
    ssize_t target_size;
    int fd;
    int rc;

    if (expected == NULL || expected->leaf == NULL ||
        expected->sha256 == NULL || expected->size <= 0) {
        return -EINVAL;
    }
    rc = d3_join(path, sizeof(path), A90_D3_ROOT, expected->leaf);
    if (rc < 0) {
        return rc;
    }
    if (lstat(path, &before) < 0 ||
        before.st_uid != (uid_t)expected->uid ||
        before.st_gid != (gid_t)expected->gid ||
        (before.st_mode & 0777) != (mode_t)expected->mode ||
        before.st_size != (off_t)expected->size) {
        return -EPERM;
    }
    if (expected->kind == D4_RO_CONTENT_REGULAR) {
        if (!S_ISREG(before.st_mode) || S_ISLNK(before.st_mode)) {
            return -EPERM;
        }
        open_flags |= O_NOFOLLOW;
    } else if (expected->kind == D4_RO_CONTENT_SYMLINK) {
        if (!S_ISLNK(before.st_mode) || expected->link_target == NULL) {
            return -EPERM;
        }
        target_size = readlink(path, target, sizeof(target) - 1U);
        if (target_size < 0 || (size_t)target_size >= sizeof(target)) {
            return target_size < 0 ? -errno : -EOVERFLOW;
        }
        target[target_size] = '\0';
        if (strcmp(target, expected->link_target) != 0) {
            return -EPERM;
        }
    } else {
        return -EINVAL;
    }
    fd = open(path, open_flags);
    if (fd < 0) {
        return -errno;
    }
    if (fstat(fd, &opened) < 0 || !S_ISREG(opened.st_mode) ||
        opened.st_uid != 0 || opened.st_gid != 0 || opened.st_size <= 0 ||
        opened.st_size > 64LL * 1024LL * 1024LL ||
        (expected->kind == D4_RO_CONTENT_REGULAR &&
         (opened.st_dev != before.st_dev ||
          opened.st_ino != before.st_ino ||
          opened.st_mode != before.st_mode ||
          opened.st_size != before.st_size))) {
        int saved_errno = errno != 0 ? errno : ESTALE;

        close(fd);
        return -saved_errno;
    }
    rc = d4_userdata_ro_hash_fd(fd, opened.st_size, expected->sha256);
    if (fstat(fd, &opened_after) < 0) {
        if (rc == 0) {
            rc = -errno;
        }
    } else if (opened_after.st_dev != opened.st_dev ||
               opened_after.st_ino != opened.st_ino ||
               opened_after.st_mode != opened.st_mode ||
               opened_after.st_uid != opened.st_uid ||
               opened_after.st_gid != opened.st_gid ||
               opened_after.st_size != opened.st_size) {
        if (rc == 0) {
            rc = -ESTALE;
        }
    }
    if (close(fd) < 0 && rc == 0) {
        rc = -errno;
    }
    if (rc < 0 || lstat(path, &after) < 0 ||
        after.st_dev != before.st_dev ||
        after.st_ino != before.st_ino ||
        after.st_mode != before.st_mode ||
        after.st_size != before.st_size) {
        return rc < 0 ? rc : -ESTALE;
    }
    a90_console_printf("%s content=ok path=/%s kind=%s bytes=%lld\r\n",
                       A90_D4_TAG,
                       expected->leaf,
                       expected->kind == D4_RO_CONTENT_REGULAR ? "file" : "symlink",
                       expected->size);
    return 0;
}

static int d4_userdata_ro_check_nonempty(const char *leaf,
                                         unsigned int expected_mode,
                                         bool exact_mode) {
    char path[PATH_MAX];
    struct stat st;
    int rc = d3_join(path, sizeof(path), A90_D3_ROOT, leaf);

    if (rc < 0) {
        return rc;
    }
    if (lstat(path, &st) < 0 || !S_ISREG(st.st_mode) || S_ISLNK(st.st_mode) ||
        st.st_uid != 0 || st.st_gid != 0 || st.st_nlink != 1 || st.st_size <= 0 ||
        (exact_mode && (st.st_mode & 0777) != (mode_t)expected_mode) ||
        (!exact_mode && (st.st_mode & 0022) != 0)) {
        return -EPERM;
    }
    return 0;
}

static int d4_userdata_ro_require_absent(const char *leaf) {
    char path[PATH_MAX];
    struct stat st;
    int rc = d3_join(path, sizeof(path), A90_D3_ROOT, leaf);

    if (rc < 0) {
        return rc;
    }
    if (lstat(path, &st) == 0) {
        return -EPERM;
    }
    return errno == ENOENT ? 0 : -errno;
}

static int d4_userdata_ro_check_usrmerge(void) {
    static const struct {
        const char *leaf;
        const char *target;
    } links[] = {
        { "bin", "usr/bin" },
        { "lib", "usr/lib" },
        { "sbin", "usr/sbin" },
    };
    size_t index;

    for (index = 0; index < sizeof(links) / sizeof(links[0]); ++index) {
        char path[PATH_MAX];
        int rc = d3_join(path, sizeof(path), A90_D3_ROOT, links[index].leaf);

        if (rc < 0) {
            return rc;
        }
        rc = d4_symlink_target_ok(path, links[index].target);
        if (rc < 0) {
            return rc;
        }
    }
    return 0;
}

static int d4_userdata_ro_check_content(
    const char *expected_content_manifest_sha256) {
    static const char *const absent[] = {
        "etc/a90-dpublic/cloudflared-quick-enable",
        "etc/a90-dpublic/native-uplink-enable",
        "etc/a90-dpublic/wpa_supplicant-wlan0.conf",
    };
    size_t index;
    int rc;

    if (expected_content_manifest_sha256 == NULL ||
        strcmp(expected_content_manifest_sha256,
               A90_D4_H14_CONTENT_MANIFEST_SHA256) != 0) {
        return -EINVAL;
    }
    rc = d4_userdata_ro_check_usrmerge();
    if (rc < 0) {
        return rc;
    }
    for (index = 0; index < sizeof(d4_h14_content) / sizeof(d4_h14_content[0]); ++index) {
        rc = d4_userdata_ro_check_content_one(&d4_h14_content[index]);
        if (rc < 0) {
            a90_console_printf("%s content=invalid index=%zu path=/%s rc=%d\r\n",
                               A90_D4_TAG,
                               index,
                               d4_h14_content[index].leaf,
                               rc);
            return rc;
        }
    }
    rc = d4_userdata_ro_check_nonempty("root/.ssh/authorized_keys", 0600, true);
    if (rc < 0) {
        return rc;
    }
    rc = d4_userdata_ro_check_nonempty("etc/a90-dpublic/wifi-sta-enable", 0, false);
    if (rc < 0) {
        return rc;
    }
    rc = d4_userdata_ro_check_nonempty(
        "etc/a90-dpublic/wifi-sta-immediate-snapshot-only", 0, false);
    if (rc < 0) {
        return rc;
    }
    for (index = 0; index < sizeof(absent) / sizeof(absent[0]); ++index) {
        rc = d4_userdata_ro_require_absent(absent[index]);
        if (rc < 0) {
            return rc;
        }
    }
    a90_console_printf(
        "%s content_manifest=ok sha256=%s files=%zu secrets_hashed=0 public_tunnel=disabled\r\n",
        A90_D4_TAG,
        expected_content_manifest_sha256,
        sizeof(d4_h14_content) / sizeof(d4_h14_content[0]));
    return 0;
}

static int d4_userdata_ro_check_root(
    const char *expected_marker,
    const char *expected_content_manifest_sha256) {
    int rc = d4_userdata_ro_check_marker(expected_marker);

    return rc < 0
               ? rc
               : d4_userdata_ro_check_content(expected_content_manifest_sha256);
}

#if A90_UFS_FIRSTBOOT_OVERLAY_V1
static int h17_bind_firstboot(bool *bound_out) {
    char target[PATH_MAX];
    struct stat source_st;
    struct stat target_before;
    struct stat target_after;
    struct statvfs target_fs;
    int rc;

    if (bound_out == NULL) {
        return -EINVAL;
    }
    *bound_out = false;
    if (lstat(A90_H17_FIRSTBOOT_SOURCE, &source_st) < 0 ||
        !S_ISREG(source_st.st_mode) || S_ISLNK(source_st.st_mode) ||
        source_st.st_nlink != 1 || (source_st.st_mode & 0777) != 0500 ||
        source_st.st_size < 4096 || source_st.st_size > 65536) {
        return -EPERM;
    }
    rc = d4_join_root(target, sizeof(target), "etc/a90-d3-firstboot");
    if (rc < 0) {
        return rc;
    }
    if (lstat(target, &target_before) < 0 ||
        !S_ISREG(target_before.st_mode) || S_ISLNK(target_before.st_mode)) {
        return -EPERM;
    }
    if (mount(A90_H17_FIRSTBOOT_SOURCE, target, NULL, MS_BIND, NULL) < 0) {
        return -errno;
    }
    *bound_out = true;
    if (mount(NULL,
              target,
              NULL,
              MS_REMOUNT | MS_BIND | MS_RDONLY | MS_NOSUID | MS_NODEV,
              NULL) < 0) {
        rc = -errno;
        goto fail_bound;
    }
    if (stat(target, &target_after) < 0 ||
        target_after.st_dev != source_st.st_dev ||
        target_after.st_ino != source_st.st_ino ||
        access(target, X_OK) < 0 ||
        statvfs(target, &target_fs) < 0 ||
        (target_fs.f_flag & ST_RDONLY) == 0) {
        rc = -ESTALE;
        goto fail_bound;
    }
    a90_console_printf(
        "%s firstboot_overlay=ready source=boot-public target=/etc/a90-d3-firstboot "
        "mount=bind-ro nosuid=1 nodev=1 ufs_write=0\r\n",
        A90_H17_TAG);
    return 0;

fail_bound:
    if (umount2(target, MNT_DETACH) < 0) {
        return -errno;
    }
    *bound_out = false;
    return rc;
}

static int h17_unbind_firstboot(void) {
    char target[PATH_MAX];
    int rc = d4_join_root(target, sizeof(target), "etc/a90-d3-firstboot");

    if (rc < 0) {
        return rc;
    }
    return umount2(target, MNT_DETACH) < 0 ? -errno : 0;
}
#endif

#if A90_UFS_PERSISTENT_NATIVE_HUD_V1
static int h17_start_persistent_hud(bool *run_bound_out,
                                    bool *started_out,
                                    pid_t *pid_out) {
    struct dpublic_hud_service_opts opts;
    pid_t hud_pid;
    int rc;

    if (run_bound_out == NULL || started_out == NULL || pid_out == NULL) {
        return -EINVAL;
    }
    *run_bound_out = false;
    *started_out = false;
    *pid_out = -1;
    rc = d4_bind_dpublic_hud_run_dir(run_bound_out);
    if (rc < 0) {
        return rc;
    }
    dpublic_hud_service_default_opts(&opts);
    opts.preopen_drm = true;
    rc = dpublic_hud_service_start(&opts, pid_out);
    if (rc < 0) {
        int unbind_rc;

        if (*pid_out > 0 && d_handoff_pid_alive(*pid_out)) {
            *started_out = true;
            return rc;
        }
        *pid_out = -1;
        unbind_rc = d4_unbind_dpublic_hud_run_dir();
        if (unbind_rc < 0) {
            return unbind_rc;
        }
        *run_bound_out = false;
        return rc;
    }
    *started_out = true;
    rc = dpublic_hud_service_status(&opts);
    if (rc == 0) {
        rc = dpublic_hud_service_read_pid(opts.pid_path, &hud_pid);
    }
    if (rc == 0 &&
        (hud_pid != *pid_out ||
         !dpublic_hud_service_pid_is_default(hud_pid) ||
         !d_handoff_pid_has_drm_fd(hud_pid))) {
        rc = -EPERM;
    }
    if (rc < 0) {
        int stop_rc;
        int unbind_rc;

        opts.release_drm = true;
        stop_rc = dpublic_hud_service_stop(&opts);
        if (stop_rc == 0) {
            *started_out = false;
            *pid_out = -1;
        } else {
            rc = stop_rc;
        }
        unbind_rc = d4_unbind_dpublic_hud_run_dir();
        if (unbind_rc == 0) {
            *run_bound_out = false;
        } else {
            rc = unbind_rc;
        }
        return rc;
    }
    a90_console_printf(
        "%s persistent_hud=ready owner=native-init-child drm_fd=1 "
        "shared_run=1 survives_switch_root=1\r\n",
        A90_H17_TAG);
    return 0;
}

static int h17_stop_persistent_hud(bool *started,
                                   bool *run_bound,
                                   pid_t *pid) {
    int rc = 0;

    if (started != NULL && *started && pid != NULL && *pid > 0) {
        struct dpublic_hud_service_opts opts;
        pid_t published_pid;

        dpublic_hud_service_default_opts(&opts);
        opts.release_drm = true;
        if (dpublic_hud_service_read_pid(opts.pid_path, &published_pid) == 0 &&
            published_pid == *pid) {
            rc = dpublic_hud_service_stop(&opts);
        } else {
            rc = d_handoff_stop_drm_owner(A90_DPUBLIC_HUD_SERVICE_TAG, *pid);
        }
        if (rc == 0) {
            *started = false;
            *pid = -1;
        }
    }
    if (run_bound != NULL && *run_bound) {
        int unbind_rc = d4_unbind_dpublic_hud_run_dir();

        if (unbind_rc == 0) {
            *run_bound = false;
        } else if (rc == 0) {
            rc = unbind_rc;
        }
    }
    return rc;
}
#endif

int a90_server_distro_userdata_ro_qualify(const char *expected_devname,
                                          const char *expected_devt_binding,
                                          const char *expected_sectors,
                                          const char *expected_label,
                                          const char *expected_marker,
                                          const char *expected_uuid,
                                          const char *expected_content_manifest_sha256) {
    struct d4_userdata_target target;
    struct d4_userdata_target final_target;
    int cleanup_rc;
    int rc;

    rc = d4_userdata_ro_expected_values_valid(expected_devname,
                                               expected_devt_binding,
                                               expected_sectors,
                                               expected_label,
                                               expected_marker,
                                               expected_uuid,
                                               expected_content_manifest_sha256);
    if (rc < 0) {
        a90_console_printf(
            "%s stop=compiled-readonly-identity-invalid rc=%d\r\n",
            A90_D4_TAG,
            rc);
        a90_logf("server-distro",
                 "D4 compiled read-only identity invalid rc=%d",
                 rc);
        return rc;
    }
    rc = d4_userdata_ro_static_preflight(expected_devname,
                                          expected_devt_binding,
                                          expected_sectors,
                                          expected_label,
                                          expected_uuid,
                                          "userdata-ro-qualification-initial",
                                          &target);
    if (rc < 0) {
        return rc;
    }
    if (mount(NULL, "/", NULL, MS_REC | MS_PRIVATE, NULL) < 0) {
        return -errno;
    }
    rc = d4_mount_userdata_readonly_no_replay();
    if (rc < 0) {
        return rc;
    }
    rc = d4_userdata_ro_check_root(expected_marker,
                                   expected_content_manifest_sha256);
    cleanup_rc = umount2(A90_D3_ROOT, MNT_DETACH) < 0 ? -errno : 0;
    if (cleanup_rc < 0) {
        a90_console_printf("%s qualification=unmount-fail root=%s rc=%d\r\n",
                           A90_D4_TAG,
                           A90_D3_ROOT,
                           cleanup_rc);
        return cleanup_rc;
    }
    if (rc < 0) {
        a90_console_printf("%s qualification=root-content-fail rc=%d\r\n",
                           A90_D4_TAG,
                           rc);
        return rc;
    }
    rc = d4_userdata_ro_static_preflight(expected_devname,
                                          expected_devt_binding,
                                          expected_sectors,
                                          expected_label,
                                          expected_uuid,
                                          "userdata-ro-qualification-final",
                                          &final_target);
    if (rc < 0) {
        return rc;
    }
    if (target.major_num != final_target.major_num ||
        target.minor_num != final_target.minor_num ||
        target.sectors != final_target.sectors ||
        strcmp(target.devname, final_target.devname) != 0) {
        return -ESTALE;
    }
    a90_console_printf(
        "%s qualification=ok root_kind=userdata-ext4-ro-noload "
        "device=%u:%u devt_binding=%s sectors=%s label=%s marker=%s uuid=%s "
        "content_manifest_sha256=%s userdata_write=0\r\n",
        A90_D4_TAG,
        final_target.major_num,
        final_target.minor_num,
        expected_devt_binding,
        expected_sectors,
        expected_label,
        expected_marker,
        expected_uuid,
        expected_content_manifest_sha256);
    return 0;
}

static void d4_record_handoff_failure(const char *stage,
                                      int rc,
                                      bool root_mounted,
                                      unsigned writable_mounted,
                                      bool evidence_bound,
                                      bool wifi_handoff_bound) {
    a90_console_printf(
        "%s handoff_stop stage=%s rc=%d errno=%d root_mounted=%d "
        "writable_mounted=%u evidence_bound=%d wifi_handoff_bound=%d\r\n",
        A90_D4_TAG,
        stage,
        rc,
        rc < 0 ? -rc : 0,
        root_mounted ? 1 : 0,
        writable_mounted,
        evidence_bound ? 1 : 0,
        wifi_handoff_bound ? 1 : 0);
    a90_logf(
        "server-distro",
        "D4 handoff stop stage=%s rc=%d errno=%d root_mounted=%d "
        "writable_mounted=%u evidence_bound=%d wifi_handoff_bound=%d",
        stage,
        rc,
        rc < 0 ? -rc : 0,
        root_mounted ? 1 : 0,
        writable_mounted,
        evidence_bound ? 1 : 0,
        wifi_handoff_bound ? 1 : 0);
}

static void d4_record_handoff_cleanup_failure(const char *stage, int rc) {
    a90_console_printf("%s handoff_cleanup_stop stage=%s rc=%d errno=%d\r\n",
                       A90_D4_TAG,
                       stage,
                       rc,
                       rc < 0 ? -rc : 0);
    a90_logf("server-distro",
             "D4 handoff cleanup stop stage=%s rc=%d errno=%d",
             stage,
             rc,
             rc < 0 ? -rc : 0);
}

int a90_server_distro_switch_root_userdata_ro(const char *expected_devname,
                                              const char *expected_devt_binding,
                                              const char *expected_sectors,
                                              const char *expected_label,
                                              const char *expected_marker,
                                              const char *expected_uuid,
                                              const char *expected_content_manifest_sha256) {
    struct d4_userdata_target target;
    struct d4_userdata_target final_target;
    unsigned writable_mounted = 0;
    bool evidence_bound = false;
    bool wifi_handoff_bound = false;
#if A90_UFS_OBSERVER_AUTH_OVERLAY_V1
    bool h17_observer_auth_mounted = false;
#endif
#if A90_UFS_FIRSTBOOT_OVERLAY_V1
    bool h17_firstboot_bound = false;
#endif
#if A90_UFS_PERSISTENT_NATIVE_HUD_V1
    bool h17_hud_run_bound = false;
    bool h17_hud_started = false;
    pid_t h17_hud_pid = -1;
#endif
    bool root_mounted = false;
    bool moved_proc = false;
    bool moved_sys = false;
    bool moved_dev = false;
    bool mounted_new_dev = false;
    bool mounted_devpts = false;
    bool cleanup_clean = true;
    bool failure_recorded = false;
    const char *failure_stage = "compiled-identity";
    int rc;
    char *const newenv[] = {
        (char *)"HOME=/root",
        (char *)"PATH=/sbin:/bin:/usr/sbin:/usr/bin",
        (char *)"TERM=linux",
        NULL,
    };
    char *const switch_argv[] = {
        (char *)A90_D3_BUSYBOX,
        (char *)"switch_root",
        (char *)A90_D3_ROOT,
        (char *)A90_D3_INIT,
        NULL,
    };

    rc = d4_userdata_ro_expected_values_valid(expected_devname,
                                               expected_devt_binding,
                                               expected_sectors,
                                               expected_label,
                                               expected_marker,
                                               expected_uuid,
                                               expected_content_manifest_sha256);
    if (rc < 0) {
        a90_console_printf(
            "%s stop=compiled-readonly-identity-invalid rc=%d\r\n",
            A90_D4_TAG,
            rc);
        a90_logf("server-distro",
                 "D4 compiled read-only identity invalid rc=%d",
                 rc);
        return rc;
    }
    a90_console_printf(
        "%s begin root_kind=userdata-ext4-ro-noload node=%s root=%s "
        "userdata_write=0\r\n",
        A90_D4_TAG,
        A90_D4_NODE,
        A90_D3_ROOT);
#if A90_AUTO_HANDOFF_BENCHMARK_V1
    a90_benchmark_emit("handoff_begin");
#endif
    failure_stage = "userdata-preflight-initial";
    rc = d4_userdata_ro_static_preflight(expected_devname,
                                          expected_devt_binding,
                                          expected_sectors,
                                          expected_label,
                                          expected_uuid,
                                          "userdata-ro-initial",
                                          &target);
    if (rc < 0) {
        return rc;
    }
#if A90_AUTO_HANDOFF_BENCHMARK_V1
    a90_benchmark_emit("userdata_identity_initial_done");
#endif
    failure_stage = "root-directory";
    rc = d3_mkdir_p(A90_D3_ROOT, 0755);
    if (rc < 0) {
        goto fail_userdata_identity;
    }
    failure_stage = "display-owner-release";
    rc = d3_handoff_stop_display_owners_strict();
    if (rc < 0) {
        a90_console_printf("%s stop=handoff-display-owner rc=%d\r\n",
                           A90_D4_TAG,
                           rc);
        goto fail_userdata_identity;
    }
#if A90_AUTO_HANDOFF_BENCHMARK_V1
    a90_benchmark_mark("display_release_done");
#endif
    failure_stage = "userdata-preflight-post-display";
    rc = d4_userdata_ro_static_preflight(expected_devname,
                                          expected_devt_binding,
                                          expected_sectors,
                                          expected_label,
                                          expected_uuid,
                                          "userdata-ro-post-display",
                                          &final_target);
    if (rc < 0 ||
        target.major_num != final_target.major_num ||
        target.minor_num != final_target.minor_num ||
        target.sectors != final_target.sectors ||
        strcmp(target.devname, final_target.devname) != 0) {
        rc = rc < 0 ? rc : -ESTALE;
        a90_console_printf("%s stop=userdata-changed-during-display-cleanup rc=%d\r\n",
                           A90_D4_TAG,
                           rc);
        goto fail_userdata_identity;
    }
#if A90_AUTO_HANDOFF_BENCHMARK_V1
    a90_benchmark_emit("userdata_identity_post_display_done");
#endif
    failure_stage = "mount-namespace-private";
    if (mount(NULL, "/", NULL, MS_REC | MS_PRIVATE, NULL) < 0) {
        rc = -errno;
        a90_console_printf("%s mount_namespace=private-fail rc=%d\r\n",
                           A90_D4_TAG,
                           rc);
        goto fail_userdata_identity;
    }
    a90_console_printf("%s mount_namespace=private\r\n", A90_D4_TAG);
    failure_stage = "root-mount";
    rc = d4_mount_userdata_readonly_no_replay();
    if (rc < 0) {
        goto fail_before_move;
    }
    root_mounted = true;
#if A90_AUTO_HANDOFF_BENCHMARK_V1
    a90_benchmark_mark("root_mounted");
#endif
    failure_stage = "root-content";
    rc = d4_userdata_ro_check_root(expected_marker,
                                   expected_content_manifest_sha256);
    if (rc < 0) {
        a90_console_printf("%s stop=userdata-root-content-invalid rc=%d\r\n",
                           A90_D4_TAG,
                           rc);
        goto fail_before_move;
    }
    failure_stage = "writable-set-mount";
    rc = d3_mount_writable_set(&writable_mounted);
    if (rc < 0) {
        goto fail_before_move;
    }
    failure_stage = "writable-set-verify";
    rc = d3_verify_writable_set();
    if (rc < 0) {
        goto fail_before_move;
    }
#if A90_UFS_OBSERVER_AUTH_OVERLAY_V1
    failure_stage = "observer-auth-overlay";
    rc = h17_mount_observer_auth(&h17_observer_auth_mounted);
    if (rc < 0) {
        a90_console_printf("%s stop=observer-auth-overlay rc=%d\r\n",
                           A90_H17_TAG,
                           rc);
        goto fail_before_move;
    }
#if !A90_UFS_FIRSTBOOT_OVERLAY_V1
#if A90_UFS_PERSISTENT_NATIVE_HUD_V1
    a90_console_printf(
        "%s firstboot=ufs-existing firstboot_overlay=disabled "
        "persistent_native_hud=enabled ufs_write=0\r\n",
        A90_H17_TAG);
#else
    a90_console_printf(
        "%s firstboot=ufs-existing firstboot_overlay=disabled "
        "persistent_native_hud=disabled ufs_write=0\r\n",
        A90_H17_TAG);
#endif
#endif
#endif
#if A90_UFS_FIRSTBOOT_OVERLAY_V1
    failure_stage = "firstboot-overlay";
    rc = h17_bind_firstboot(&h17_firstboot_bound);
    if (rc < 0) {
        a90_console_printf("%s stop=firstboot-overlay rc=%d\r\n",
                           A90_H17_TAG,
                           rc);
        goto fail_before_move;
    }
#endif
#if A90_UFS_PERSISTENT_NATIVE_HUD_V1
    failure_stage = "persistent-hud";
    rc = h17_start_persistent_hud(
        &h17_hud_run_bound,
        &h17_hud_started,
        &h17_hud_pid);
    if (rc < 0) {
        a90_console_printf("%s stop=persistent-hud rc=%d\r\n",
                           A90_H17_TAG,
                           rc);
        goto fail_before_move;
    }
#endif
    failure_stage = "evidence-bind";
    rc = d3_bind_evidence_dir(&evidence_bound);
    if (rc < 0) {
        goto fail_before_move;
    }
    failure_stage = "wifi-handoff-bind";
    rc = d3_bind_wifi_handoff_dir(&wifi_handoff_bound);
    if (rc < 0) {
        a90_console_printf("%s stop=wifi-handoff-bind rc=%d\r\n",
                           A90_D4_TAG,
                           rc);
        goto fail_before_move;
    }
#if A90_AUTO_HANDOFF_BENCHMARK_V1
    a90_benchmark_emit("writable_set_ready");
#endif
    failure_stage = "distro-init";
    rc = d3_check_distro_init();
    if (rc < 0) {
        a90_console_printf("%s stop=distro-init-invalid rc=%d\r\n",
                           A90_D4_TAG,
                           rc);
        goto fail_before_move;
    }
#if A90_AUTO_HANDOFF_BENCHMARK_V1
    a90_benchmark_mark("distro_init_verified");
#endif
    failure_stage = "display-release-marker";
    rc = d3_write_display_release_marker(&d3_last_display_release);
    if (rc < 0) {
        a90_console_printf("%s stop=display-release-marker rc=%d\r\n",
                           A90_D4_TAG,
                           rc);
        goto fail_before_move;
    }
#if A90_AUTO_HANDOFF_BENCHMARK_V1
    a90_benchmark_mark("display_marker_ready");
#endif
    failure_stage = "core-mount-move";
    rc = d3_move_core_mounts(true,
                             &moved_proc,
                             &moved_sys,
                             &moved_dev,
                             &mounted_new_dev,
                             &mounted_devpts);
    if (rc < 0) {
        int restore_rc;

        a90_console_printf("%s mount_move=fail rc=%d\r\n", A90_D4_TAG, rc);
        d4_record_handoff_failure(failure_stage,
                                  rc,
                                  root_mounted,
                                  writable_mounted,
                                  evidence_bound,
                                  wifi_handoff_bound);
        failure_recorded = true;
        restore_rc = d3_restore_core_mounts(moved_proc,
                                            moved_sys,
                                            moved_dev,
                                            mounted_new_dev,
                                            mounted_devpts);
        if (restore_rc < 0) {
            cleanup_clean = false;
            failure_stage = "core-mount-restore";
            rc = restore_rc;
            d4_record_handoff_cleanup_failure(failure_stage, rc);
        } else {
            moved_proc = false;
            moved_sys = false;
            moved_dev = false;
            mounted_new_dev = false;
            mounted_devpts = false;
        }
        goto fail_before_move;
    }
#if A90_AUTO_HANDOFF_BENCHMARK_V1
    a90_benchmark_mark("mount_moves_done");
#endif
    a90_console_printf(
        "%s exec_switch_root_now busybox=%s root=%s init=%s "
        "source=ufs-userdata-ro-noload console=reuse-stdio\r\n",
        A90_D4_TAG,
        A90_D3_BUSYBOX,
        A90_D3_ROOT,
        A90_D3_INIT);
#if A90_UFS_OBSERVER_AUTH_OVERLAY_V1
    a90_logf("server-distro",
             "D4 read-only switch_root exec source=%s root=%s "
             "writable_set=%u evidence_bound=%d wifi_handoff_bound=%d "
             "observer_auth=%d firstboot_overlay=%d persistent_native_hud=%d",
             A90_D4_NODE,
             A90_D3_ROOT,
             writable_mounted,
             evidence_bound ? 1 : 0,
             wifi_handoff_bound ? 1 : 0,
             h17_observer_auth_mounted ? 1 : 0,
#if A90_UFS_FIRSTBOOT_OVERLAY_V1
             h17_firstboot_bound ? 1 : 0,
#else
             0,
#endif
#if A90_UFS_PERSISTENT_NATIVE_HUD_V1
             h17_hud_started ? 1 : 0);
#else
             0);
#endif
#else
    a90_logf("server-distro",
             "D4 read-only switch_root exec source=%s root=%s "
             "writable_set=%u evidence_bound=%d wifi_handoff_bound=%d",
             A90_D4_NODE,
             A90_D3_ROOT,
             writable_mounted,
             evidence_bound ? 1 : 0,
             wifi_handoff_bound ? 1 : 0);
#endif
#if A90_AUTO_HANDOFF_BENCHMARK_V1
    a90_benchmark_mark("switch_root_exec");
#endif
    sync();
    usleep(200000);
    failure_stage = "switch-root-exec";
    execve(A90_D3_BUSYBOX, switch_argv, newenv);

    rc = -errno;
    a90_console_printf("%s execve_switch_root=fail rc=%d errno=%d (%s)\r\n",
                       A90_D4_TAG,
                       rc,
                       -rc,
                       strerror(-rc));
    d4_record_handoff_failure(failure_stage,
                              rc,
                              root_mounted,
                              writable_mounted,
                              evidence_bound,
                              wifi_handoff_bound);
    failure_recorded = true;
    {
        int restore_rc = d3_restore_core_mounts(moved_proc,
                                                moved_sys,
                                                moved_dev,
                                                mounted_new_dev,
                                                mounted_devpts);

        if (restore_rc < 0) {
            cleanup_clean = false;
            failure_stage = "core-mount-restore-after-exec";
            rc = restore_rc;
            d4_record_handoff_cleanup_failure(failure_stage, rc);
        } else {
            moved_proc = false;
            moved_sys = false;
            moved_dev = false;
            mounted_new_dev = false;
            mounted_devpts = false;
        }
    }

fail_before_move:
    if (!failure_recorded) {
        d4_record_handoff_failure(failure_stage,
                                  rc,
                                  root_mounted,
                                  writable_mounted,
                                  evidence_bound,
                                  wifi_handoff_bound);
    }
#if A90_UFS_OBSERVER_AUTH_OVERLAY_V1
#if A90_UFS_PERSISTENT_NATIVE_HUD_V1
    if (h17_stop_persistent_hud(
            &h17_hud_started,
            &h17_hud_run_bound,
            &h17_hud_pid) < 0) {
        cleanup_clean = false;
    }
#endif
#if A90_UFS_FIRSTBOOT_OVERLAY_V1
    if (h17_firstboot_bound) {
        if (h17_unbind_firstboot() < 0) {
            cleanup_clean = false;
        } else {
            h17_firstboot_bound = false;
        }
    }
#endif
    if (h17_observer_auth_mounted) {
        if (h17_unmount_observer_auth() < 0) {
            cleanup_clean = false;
        } else {
            h17_observer_auth_mounted = false;
        }
    }
#endif
    if (root_mounted && cleanup_clean) {
        if (umount2(A90_D3_ROOT, MNT_DETACH) == 0) {
            a90_console_printf("%s rootfs=unmounted-after-fail root=%s\r\n",
                               A90_D4_TAG,
                               A90_D3_ROOT);
            root_mounted = false;
        } else {
            cleanup_clean = false;
            a90_console_printf("%s rootfs=unmount-fail root=%s errno=%d\r\n",
                               A90_D4_TAG,
                               A90_D3_ROOT,
                               errno);
        }
    } else if (root_mounted) {
        a90_console_printf(
            "%s rootfs=retained-after-restore-fail root=%s recovery_required=1\r\n",
            A90_D4_TAG,
            A90_D3_ROOT);
    }
    a90_console_printf("%s mount_state_clean_after_failure=%d\r\n",
                       A90_D4_TAG,
                       cleanup_clean ? 1 : 0);

fail_userdata_identity:
    if (d4_userdata_ro_static_preflight(expected_devname,
                                         expected_devt_binding,
                                         expected_sectors,
                                         expected_label,
                                         expected_uuid,
                                         "userdata-ro-after-failure",
                                         &final_target) < 0) {
        a90_console_printf(
            "%s userdata_unchanged_after_failure=0 stop=identity-lost\r\n",
            A90_D4_TAG);
        return -ESTALE;
    }
    a90_console_printf("%s userdata_unchanged_after_failure=1 userdata_write=0\r\n",
                       A90_D4_TAG);
    a90_logf("server-distro",
             "D4 handoff failure cleanup_clean=%d root_mounted=%d "
             "recovery_required=%d userdata_unchanged=1 userdata_write=0",
             cleanup_clean ? 1 : 0,
             root_mounted ? 1 : 0,
             (cleanup_clean && !root_mounted) ? 0 : 1);
#if A90_AUTO_HANDOFF_BENCHMARK_V1
    a90_benchmark_emit("handoff_failed_native");
#endif
    return rc;
}

static int d4_dpublic_hud_bind_target(char *out, size_t out_size) {
    return d4_join_root(out, out_size, "run/a90-dpublic");
}

static int d4_unbind_dpublic_hud_run_dir(void) {
    char dst[PATH_MAX];
    int rc = d4_dpublic_hud_bind_target(dst, sizeof(dst));

    if (rc < 0) {
        return rc;
    }
    return umount2(dst, MNT_DETACH) < 0 ? -errno : 0;
}

static int d4_bind_dpublic_hud_run_dir(bool *bound_out) {
    char dst[PATH_MAX];
    struct stat src_st;
    struct stat dst_st;
    int mounted;
    int cleanup_rc;
    int rc;

    if (bound_out != NULL) {
        *bound_out = false;
    }
    rc = dpublic_hud_service_prepare_run_dir();
    if (rc < 0) {
        a90_console_printf("%s shared_run_dir=prepare-fail rc=%d\r\n",
                           A90_DPUBLIC_HUD_SERVICE_SHARED_TAG, rc);
        return rc;
    }
    rc = d4_dpublic_hud_bind_target(dst, sizeof(dst));
    if (rc < 0) {
        return rc;
    }
    rc = d3_mkdir_p(dst, A90_DPUBLIC_HUD_RUN_DIR_MODE);
    if (rc < 0) {
        return rc;
    }
    mounted = d3_path_is_mounted(dst);
    if (mounted < 0) {
        return mounted;
    }
    if (mounted && umount2(dst, MNT_DETACH) < 0) {
        rc = -errno;
        a90_console_printf("%s shared_run_bind=stale-unmount-fail target=%s rc=%d errno=%d (%s)\r\n",
                           A90_DPUBLIC_HUD_SERVICE_SHARED_TAG,
                           dst,
                           rc,
                           -rc,
                           strerror(-rc));
        return rc;
    }
    if (mount(A90_DPUBLIC_HUD_RUN_DIR, dst, NULL, MS_BIND, NULL) < 0) {
        rc = -errno;
        a90_console_printf("%s shared_run_bind=fail source=%s target=%s rc=%d errno=%d (%s)\r\n",
                           A90_DPUBLIC_HUD_SERVICE_SHARED_TAG,
                           A90_DPUBLIC_HUD_RUN_DIR,
                           dst,
                           rc,
                           -rc,
                           strerror(-rc));
        return rc;
    }
    if (bound_out != NULL) {
        *bound_out = true;
    }
    if (chown(dst, 0, A90_DPUBLIC_HUD_GROUP_GID) < 0) {
        rc = -errno;
        goto fail_bound;
    }
    if (chmod(dst, A90_DPUBLIC_HUD_RUN_DIR_MODE) < 0) {
        rc = -errno;
        goto fail_bound;
    }
    if (mount(NULL,
              dst,
              NULL,
              MS_REMOUNT | MS_BIND | MS_NOSUID | MS_NODEV,
              NULL) < 0) {
        rc = -errno;
        goto fail_bound;
    }
    rc = dpublic_hud_service_verify_shared_run_mount(dst);
    if (rc < 0) {
        goto fail_bound;
    }
    if (stat(A90_DPUBLIC_HUD_RUN_DIR, &src_st) < 0 ||
        stat(dst, &dst_st) < 0) {
        rc = -errno;
        goto fail_bound;
    }
    if (!S_ISDIR(src_st.st_mode) || !S_ISDIR(dst_st.st_mode) ||
        src_st.st_dev != dst_st.st_dev || src_st.st_ino != dst_st.st_ino ||
        dst_st.st_uid != 0 || dst_st.st_gid != A90_DPUBLIC_HUD_GROUP_GID ||
        (dst_st.st_mode & 07777) != A90_DPUBLIC_HUD_RUN_DIR_MODE) {
        rc = -ESTALE;
        goto fail_bound;
    }
    a90_console_printf(
        "%s shared_run_bind=ok source=%s target=%s same_dev=1 same_ino=1 "
        "fstype=tmpfs rw=1 nosuid=1 nodev=1 owner=0:%u mode=%04o\r\n",
        A90_DPUBLIC_HUD_SERVICE_SHARED_TAG,
        A90_DPUBLIC_HUD_RUN_DIR,
        dst,
        A90_DPUBLIC_HUD_GROUP_GID,
        A90_DPUBLIC_HUD_RUN_DIR_MODE);
    return 0;

fail_bound:
    cleanup_rc = 0;
    if (umount2(dst, MNT_DETACH) < 0) {
        cleanup_rc = -errno;
    } else if (bound_out != NULL) {
        *bound_out = false;
    }
    a90_console_printf(
        "%s shared_run_bind=verify-fail source=%s target=%s rc=%d cleanup_rc=%d\r\n",
        A90_DPUBLIC_HUD_SERVICE_SHARED_TAG,
        A90_DPUBLIC_HUD_RUN_DIR,
        dst,
        rc,
        cleanup_rc);
    return cleanup_rc < 0 ? cleanup_rc : rc;
}

static int d4_move_mount_one(const char *src, const char *leaf) {
    char dst[PATH_MAX];
    int rc = d4_join_root(dst, sizeof(dst), leaf);

    if (rc < 0) {
        return rc;
    }
    rc = d3_mkdir_p(dst, 0755);
    if (rc < 0) {
        return rc;
    }
    if (mount(src, dst, NULL, MS_MOVE, NULL) < 0) {
        return -errno;
    }
    a90_console_printf("%s mount_move=%s->%s ok=1\r\n", A90_D4_TAG, src, dst);
    return 0;
}

static int d4_prepare_dev_node(const char *leaf, mode_t mode, unsigned int maj, unsigned int min) {
    char path[PATH_MAX];
    int rc = d4_join_root(path, sizeof(path), leaf);

    if (rc < 0) {
        return rc;
    }
    return d3_ensure_char_node_at(path, mode, maj, min);
}

static int d4_prepare_optional_ttygs0(void) {
    struct stat st;

    if (stat("/dev/ttyGS0", &st) < 0) {
        a90_console_printf("%s dev_node_optional=/dev/ttyGS0 missing errno=%d\r\n",
                           A90_D4_TAG, errno);
        return 0;
    }
    if (!S_ISCHR(st.st_mode)) {
        a90_console_printf("%s dev_node_optional=/dev/ttyGS0 not-char\r\n", A90_D4_TAG);
        return 0;
    }
    return d4_prepare_dev_node("dev/ttyGS0", 0600, major(st.st_rdev), minor(st.st_rdev));
}

static int d4_prepare_new_dev(bool *mounted_devpts) {
    char dev_dir[PATH_MAX];
    char pts_dir[PATH_MAX];
    int rc;

    if (mounted_devpts != NULL) {
        *mounted_devpts = false;
    }
    rc = d4_join_root(dev_dir, sizeof(dev_dir), "dev");
    if (rc < 0) {
        return rc;
    }
    rc = d3_mkdir_p(dev_dir, 0755);
    if (rc < 0) {
        return rc;
    }
    rc = d4_prepare_dev_node("dev/console", 0600, 5, 1);
    if (rc < 0) {
        return rc;
    }
    rc = d4_prepare_dev_node("dev/tty", 0666, 5, 0);
    if (rc < 0) {
        return rc;
    }
    rc = d4_prepare_dev_node("dev/ptmx", 0666, 5, 2);
    if (rc < 0) {
        return rc;
    }
    rc = d4_prepare_dev_node("dev/null", 0666, 1, 3);
    if (rc < 0) {
        return rc;
    }
    rc = d4_prepare_dev_node("dev/zero", 0666, 1, 5);
    if (rc < 0) {
        return rc;
    }
    rc = d4_prepare_dev_node("dev/random", 0666, 1, 8);
    if (rc < 0) {
        return rc;
    }
    rc = d4_prepare_dev_node("dev/urandom", 0666, 1, 9);
    if (rc < 0) {
        return rc;
    }
    rc = d4_prepare_optional_ttygs0();
    if (rc < 0) {
        return rc;
    }
    rc = d4_join_root(pts_dir, sizeof(pts_dir), "dev/pts");
    if (rc < 0) {
        return rc;
    }
    rc = d3_mkdir_p(pts_dir, 0755);
    if (rc < 0) {
        return rc;
    }
    if (mount("devpts", pts_dir, "devpts", 0, "mode=620,ptmxmode=666") == 0) {
        if (mounted_devpts != NULL) {
            *mounted_devpts = true;
        }
        a90_console_printf("%s devpts=mounted path=%s\r\n", A90_D4_TAG, pts_dir);
    } else {
        a90_console_printf("%s devpts=warn rc=-%d (%s)\r\n",
                           A90_D4_TAG, errno, strerror(errno));
    }
    a90_console_printf("%s dev_mountpoint=0 dev_nodes=prepared root=%s\r\n",
                       A90_D4_TAG, dev_dir);
    return 0;
}

static void d4_restore_mount_one(const char *leaf, const char *dst) {
    char src[PATH_MAX];

    if (d4_join_root(src, sizeof(src), leaf) < 0) {
        return;
    }
    (void)mount(src, dst, NULL, MS_MOVE, NULL);
}

static void d4_unmount_leaf(const char *leaf) {
    char path[PATH_MAX];

    if (d4_join_root(path, sizeof(path), leaf) < 0) {
        return;
    }
    (void)umount2(path, MNT_DETACH);
}

static int d4_move_core_mounts(bool *moved_proc,
                               bool *moved_sys,
                               bool *moved_dev,
                               bool *mounted_devpts) {
    int dev_mounted;
    int rc;

    if (moved_proc != NULL) {
        *moved_proc = false;
    }
    if (moved_sys != NULL) {
        *moved_sys = false;
    }
    if (moved_dev != NULL) {
        *moved_dev = false;
    }
    if (mounted_devpts != NULL) {
        *mounted_devpts = false;
    }
    dev_mounted = d3_path_is_mounted("/dev");
    if (dev_mounted < 0) {
        return dev_mounted;
    }
    if (mount(NULL, "/", NULL, MS_REC | MS_PRIVATE, NULL) < 0) {
        return -errno;
    }
    rc = d4_move_mount_one("/proc", "proc");
    if (rc < 0) {
        return rc;
    }
    if (moved_proc != NULL) {
        *moved_proc = true;
    }
    rc = d4_move_mount_one("/sys", "sys");
    if (rc < 0) {
        d4_restore_mount_one("proc", "/proc");
        return rc;
    }
    if (moved_sys != NULL) {
        *moved_sys = true;
    }
    if (dev_mounted) {
        rc = d4_move_mount_one("/dev", "dev");
        if (rc < 0) {
            d4_restore_mount_one("sys", "/sys");
            d4_restore_mount_one("proc", "/proc");
            return rc;
        }
        if (moved_dev != NULL) {
            *moved_dev = true;
        }
    } else {
        rc = d4_prepare_new_dev(mounted_devpts);
        if (rc < 0) {
            d4_restore_mount_one("sys", "/sys");
            d4_restore_mount_one("proc", "/proc");
            return rc;
        }
    }
    return 0;
}

static void d4_restore_core_mounts(bool moved_proc, bool moved_sys, bool moved_dev, bool mounted_devpts) {
    if (mounted_devpts) {
        d4_unmount_leaf("dev/pts");
    }
    if (moved_dev) {
        d4_restore_mount_one("dev", "/dev");
    }
    if (moved_sys) {
        d4_restore_mount_one("sys", "/sys");
    }
    if (moved_proc) {
        d4_restore_mount_one("proc", "/proc");
    }
}

int a90_server_distro_userdata_preflight_cmd(char **argv, int argc) {
    struct d4_userdata_target target;
    int rc;

    if (argc != 2 || strcmp(argv[1], A90_D4_TOKEN) != 0) {
        a90_console_printf("usage: userdata-appliance-preflight %s\r\n", A90_D4_TOKEN);
        a90_console_printf("%s refused=missing-or-wrong-token-or-argc argc=%d\r\n",
                           A90_D4_TAG, argc);
        return -EPERM;
    }
    rc = d4_resolve_userdata(&target);
    if (rc < 0) {
        a90_console_printf("%s preflight=fail rc=%d\r\n", A90_D4_TAG, rc);
        return rc;
    }
    d4_print_target(&target, "preflight");
    a90_console_printf("%s preflight=ok format_allowed=0 node_materialized=0\r\n", A90_D4_TAG);
    return 0;
}

int a90_server_distro_userdata_formatter_probe_cmd(char **argv, int argc) {
    const char *probe_path;
    unsigned long long size_bytes = 0;
    char chroot_probe_path[PATH_MAX];
    int rc;
    int cleanup_rc;

    if (argc != 4 || strcmp(argv[1], A90_D4_TOKEN) != 0) {
        a90_console_printf("usage: userdata-appliance-formatter-probe %s <probe-image> <size-bytes>\r\n",
                           A90_D4_TOKEN);
        a90_console_printf("%s refused=missing-or-wrong-token-or-argc argc=%d\r\n",
                           A90_D4_TAG, argc);
        return -EPERM;
    }
    probe_path = argv[2];
    if (!d4_source_path_clean(probe_path)) {
        a90_console_printf("%s refused=probe-path-outside-approved-sd-runtime path=%s\r\n",
                           A90_D4_TAG, probe_path);
        return -EPERM;
    }
    rc = d4_chroot_path_for_toolroot_file(probe_path,
                                          chroot_probe_path,
                                          sizeof(chroot_probe_path));
    if (rc < 0) {
        return rc;
    }
    rc = d4_parse_u64(argv[3], &size_bytes);
    if (rc < 0 ||
        size_bytes < A90_D4_FORMATTER_PROBE_MIN_BYTES ||
        size_bytes > A90_D4_FORMATTER_PROBE_MAX_BYTES) {
        a90_console_printf("%s refused=bad-probe-size size=%s min=%llu max=%llu\r\n",
                           A90_D4_TAG, argv[3],
                           A90_D4_FORMATTER_PROBE_MIN_BYTES,
                           A90_D4_FORMATTER_PROBE_MAX_BYTES);
        return -EINVAL;
    }
    if ((size_bytes % 1024ULL) != 0) {
        a90_console_printf("%s refused=bad-probe-size-alignment size=%llu alignment=1024\r\n",
                           A90_D4_TAG, size_bytes);
        return -EINVAL;
    }

    rc = d4_verify_e2fs_toolroot();
    if (rc < 0) {
        return rc;
    }
    rc = d4_create_probe_file(probe_path, size_bytes);
    if (rc < 0) {
        return rc;
    }
    rc = d4_run_e2fs_mkfs_ext4("A90D4PROBE", chroot_probe_path, "formatter-probe");
    if (rc < 0) {
        (void)unlink(probe_path);
        return rc;
    }
    rc = d4_check_ext4_magic_phase(probe_path, "formatter-probe");
    if (rc < 0) {
        (void)unlink(probe_path);
        return rc;
    }
    rc = d4_run_e2fs_dumpe2fs_header(chroot_probe_path, "formatter-probe");
    if (rc < 0) {
        (void)unlink(probe_path);
        return rc;
    }
    rc = d4_check_ext_has_journal(probe_path, "formatter-probe");
    if (rc < 0) {
        (void)unlink(probe_path);
        return rc;
    }
    cleanup_rc = unlink(probe_path);
    if (cleanup_rc < 0) {
        rc = -errno;
        a90_console_printf("%s formatter-probe=cleanup-fail path=%s rc=%d\r\n",
                           A90_D4_TAG, probe_path, rc);
        return rc;
    }
    sync();
    a90_console_printf("%s formatter-probe=done formatter=e2fsprogs-mkfs.ext4 path=%s cleanup=ok userdata_touched=0 has_journal=1\r\n",
                       A90_D4_TAG, probe_path);
    return 0;
}

int a90_server_distro_userdata_format_cmd(char **argv, int argc) {
    struct d4_userdata_target target;
    int rc;

    if (argc != 5 || strcmp(argv[1], A90_D4_TOKEN) != 0) {
        a90_console_printf("usage: userdata-appliance-format %s <expected-devname> <expected-dev> <expected-sectors>\r\n",
                           A90_D4_TOKEN);
        a90_console_printf("%s refused=missing-or-wrong-token-or-argc argc=%d\r\n",
                           A90_D4_TAG, argc);
        return -EPERM;
    }
    rc = d4_resolve_userdata(&target);
    if (rc < 0) {
        a90_console_printf("%s format=fail stage=resolve rc=%d\r\n", A90_D4_TAG, rc);
        return rc;
    }
    d4_print_target(&target, "format-ready-check");
    if (target.mounted) {
        a90_console_printf("%s stop=target-mounted-before-format\r\n", A90_D4_TAG);
        return -EBUSY;
    }
    rc = d4_compare_expected(&target, argv[2], argv[3], argv[4]);
    if (rc < 0) {
        return rc;
    }
    rc = d4_verify_e2fs_toolroot();
    if (rc < 0) {
        a90_console_printf("%s format=fail stage=e2fs-toolroot rc=%d\r\n", A90_D4_TAG, rc);
        return rc;
    }
    rc = d4_ensure_userdata_node(&target);
    if (rc < 0) {
        a90_console_printf("%s format=fail stage=node rc=%d\r\n", A90_D4_TAG, rc);
        return rc;
    }
    rc = d4_ensure_toolroot_userdata_node(&target);
    if (rc < 0) {
        a90_console_printf("%s format=fail stage=e2fs-toolroot-node rc=%d\r\n", A90_D4_TAG, rc);
        return rc;
    }
    rc = d4_run_e2fs_mkfs_ext4("A90D4ROOT", A90_D4_NODE, "format");
    if (rc < 0) {
        return rc;
    }
    rc = d4_check_ext4_magic_phase(A90_D4_NODE, "format");
    if (rc < 0) {
        a90_console_printf("%s format=fail stage=ext-magic rc=%d\r\n", A90_D4_TAG, rc);
        return rc;
    }
    rc = d4_run_e2fs_dumpe2fs_header(A90_D4_NODE, "format");
    if (rc < 0) {
        return rc;
    }
    rc = d4_check_ext_has_journal(A90_D4_NODE, "format");
    if (rc < 0) {
        a90_console_printf("%s format=fail stage=has-journal rc=%d\r\n", A90_D4_TAG, rc);
        return rc;
    }
    sync();
    a90_console_printf("%s format=done formatter=e2fsprogs-mkfs.ext4 node=%s label=A90D4ROOT has_journal=1\r\n",
                       A90_D4_TAG, A90_D4_NODE);
    return 0;
}

int a90_server_distro_userdata_populate_cmd(char **argv, int argc) {
    const char *source_tar;
    const char *expected_sha;
    char actual_sha[65];
    struct d4_userdata_target target;
    char *tar_argv[7];
    int rc;

    if (argc != 4 || strcmp(argv[1], A90_D4_TOKEN) != 0) {
        a90_console_printf("usage: userdata-appliance-populate %s <source-tar> <sha256>\r\n",
                           A90_D4_TOKEN);
        a90_console_printf("%s refused=missing-or-wrong-token-or-argc argc=%d\r\n",
                           A90_D4_TAG, argc);
        return -EPERM;
    }
    source_tar = argv[2];
    expected_sha = argv[3];
    if (!d4_source_path_clean(source_tar)) {
        a90_console_printf("%s refused=path-outside-approved-sd-runtime source=%s\r\n",
                           A90_D4_TAG, source_tar);
        return -EPERM;
    }
    if (!d3_hex64_valid(expected_sha)) {
        a90_console_printf("%s refused=bad-expected-sha\r\n", A90_D4_TAG);
        return -EINVAL;
    }
    rc = d4_regular_file_ok(source_tar);
    if (rc < 0) {
        return rc;
    }
    if (a90_helper_sha256_file(source_tar, actual_sha, sizeof(actual_sha)) != 0) {
        a90_console_printf("%s sha=compute-fail\r\n", A90_D4_TAG);
        return -EIO;
    }
    if (!d3_sha_equal_ci(actual_sha, expected_sha)) {
        a90_console_printf("%s sha=%s expected_sha_match=0 stop=sha-mismatch\r\n",
                           A90_D4_TAG, actual_sha);
        return -EPERM;
    }
    a90_console_printf("%s sha=%s expected_sha_match=1 source=%s\r\n",
                       A90_D4_TAG, actual_sha, source_tar);
    rc = d4_resolve_userdata(&target);
    if (rc < 0) {
        return rc;
    }
    d4_print_target(&target, "populate-ready-check");
    rc = d4_ensure_userdata_node(&target);
    if (rc < 0) {
        return rc;
    }
    rc = d4_mount_userdata_root();
    if (rc < 0) {
        return rc;
    }
    tar_argv[0] = (char *)A90_D4_BUSYBOX;
    tar_argv[1] = (char *)"tar";
    tar_argv[2] = (char *)"-xpf";
    tar_argv[3] = (char *)source_tar;
    tar_argv[4] = (char *)"-C";
    tar_argv[5] = (char *)A90_D4_ROOT;
    tar_argv[6] = NULL;
    a90_console_printf("%s populate=begin source=%s root=%s\r\n",
                       A90_D4_TAG, source_tar, A90_D4_ROOT);
    rc = d4_run_busybox(tar_argv, A90_D4_POPULATE_TIMEOUT_MS);
    if (rc != 0) {
        a90_console_printf("%s populate=fail stage=tar rc=%d\r\n", A90_D4_TAG, rc);
        return rc > 0 ? -EIO : rc;
    }
    rc = d4_check_userdata_init();
    if (rc < 0) {
        a90_console_printf("%s populate=fail stage=init rc=%d\r\n", A90_D4_TAG, rc);
        return rc;
    }
    rc = d4_write_marker();
    if (rc < 0) {
        a90_console_printf("%s populate=fail stage=marker rc=%d\r\n", A90_D4_TAG, rc);
        return rc;
    }
    sync();
    a90_console_printf("%s populate=done root=%s marker=%s\r\n",
                       A90_D4_TAG, A90_D4_ROOT, A90_D4_MARKER_VALUE);
    return 0;
}

int a90_server_distro_switch_root_userdata_cmd(char **argv, int argc) {
    const char *expected_marker;
    char actual_marker[128];
    struct d4_userdata_target target;
    bool moved_proc = false;
    bool moved_sys = false;
    bool moved_dev = false;
    bool mounted_devpts = false;
    bool bound_dpublic_hud_run = false;
    int rc;
    char *const newenv[] = {
        (char *)"HOME=/root",
        (char *)"PATH=/sbin:/bin:/usr/sbin:/usr/bin",
        (char *)"TERM=linux",
        NULL,
    };
    char *const switch_argv[] = {
        (char *)A90_D4_BUSYBOX,
        (char *)"switch_root",
        (char *)A90_D4_ROOT,
        (char *)A90_D4_INIT,
        NULL,
    };

    if (argc != 3 || strcmp(argv[1], A90_D4_TOKEN) != 0) {
        a90_console_printf("usage: switch-root-to-userdata %s <expected-marker>\r\n", A90_D4_TOKEN);
        a90_console_printf("%s refused=missing-or-wrong-token-or-argc argc=%d\r\n",
                           A90_D4_TAG, argc);
        return -EPERM;
    }
    expected_marker = argv[2];
    if (!d4_marker_clean(expected_marker)) {
        a90_console_printf("%s refused=bad-expected-marker\r\n", A90_D4_TAG);
        return -EINVAL;
    }
    rc = d4_resolve_userdata(&target);
    if (rc < 0) {
        return rc;
    }
    d4_print_target(&target, "switch-ready-check");
    rc = d4_ensure_userdata_node(&target);
    if (rc < 0) {
        return rc;
    }
    rc = d4_mount_userdata_root();
    if (rc < 0) {
        return rc;
    }
    rc = d4_read_marker(actual_marker, sizeof(actual_marker));
    if (rc < 0) {
        a90_console_printf("%s stop=marker-read-fail rc=%d\r\n", A90_D4_TAG, rc);
        return rc;
    }
    if (strcmp(actual_marker, expected_marker) != 0) {
        a90_console_printf("%s stop=marker-mismatch marker=%s expected=%s\r\n",
                           A90_D4_TAG, actual_marker, expected_marker);
        return -EPERM;
    }
    a90_console_printf("%s marker=ok value=%s\r\n", A90_D4_TAG, actual_marker);
    rc = d4_check_userdata_init();
    if (rc < 0) {
        a90_console_printf("%s stop=appliance-init-invalid rc=%d\r\n", A90_D4_TAG, rc);
        return rc;
    }
    rc = d_handoff_stop_display_owners(A90_D4_TAG);
    if (rc < 0) {
        a90_console_printf("%s stop=handoff-display-owner rc=%d\r\n", A90_D4_TAG, rc);
        return rc;
    }
    rc = d4_bind_dpublic_hud_run_dir(&bound_dpublic_hud_run);
    if (rc < 0) {
        a90_console_printf("%s stop=dpublic-hud-shared-run-bind rc=%d\r\n", A90_D4_TAG, rc);
        return rc;
    }
    rc = d4_move_core_mounts(&moved_proc, &moved_sys, &moved_dev, &mounted_devpts);
    if (rc < 0) {
        a90_console_printf("%s mount_move=fail rc=%d\r\n", A90_D4_TAG, rc);
        if (bound_dpublic_hud_run) {
            d4_unbind_dpublic_hud_run_dir();
        }
        return rc;
    }

    a90_console_printf("%s exec_switch_root_now busybox=%s root=%s init=%s marker=%s\r\n",
                       A90_D4_TAG, A90_D4_BUSYBOX, A90_D4_ROOT, A90_D4_INIT, actual_marker);
    a90_logf("server-distro", "D4 switch_root exec root=%s marker=%s", A90_D4_ROOT, actual_marker);
    sync();
    usleep(200000);
    execve(A90_D4_BUSYBOX, switch_argv, newenv);

    rc = -errno;
    a90_console_printf("%s execve_switch_root=fail rc=%d errno=%d (%s)\r\n",
                       A90_D4_TAG, rc, -rc, strerror(-rc));
    d4_restore_core_mounts(moved_proc, moved_sys, moved_dev, mounted_devpts);
    if (bound_dpublic_hud_run) {
        d4_unbind_dpublic_hud_run_dir();
    }
    return rc;
}
