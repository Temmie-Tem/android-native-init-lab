#include "a90_server_distro.h"

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
#include <limits.h>
#include <stdbool.h>
#include <stdint.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/stat.h>
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
#define A90_D3_LOOP "/dev/loop0"
#define A90_D3_BUSYBOX "/bin/busybox"
#define A90_D3_INIT "/sbin/init"
#define A90_D3_SWITCH_TIMEOUT_MS 30000
#define A90_D_HANDOFF_HUD_TIMEOUT_MS 3000
#define A90_D_HANDOFF_DRM_OWNER_TIMEOUT_MS 1000
#define A90_D_HW_TAG "A90DHW"
#define A90_DPUBLIC_HUD_TAG "A90WSTA136"
#define A90_DPUBLIC_HUD_SERVICE_TAG "A90WSTA140"
#define A90_DPUBLIC_HUD_SERVICE_DEDUP_TAG "A90WSTA142"
#define A90_DPUBLIC_HUD_SERVICE_DEDUP_MODE "same-content-consumed-or-rejected"
#define A90_DPUBLIC_HUD_SERVICE_SHARED_TAG "A90WSTA144"
#define A90_DPUBLIC_HUD_SERVICE_SHARED_MODE "shared-run-dir-bind-before-switch-root"
#define A90_DPUBLIC_HUD_RUN_DIR "/run/a90-dpublic"
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

static int d3_path_is_mounted(const char *mountpoint);

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

static bool d_handoff_pid_has_drm_fd(pid_t pid) {
    char dir_path[64];
    DIR *dir;
    struct dirent *entry;
    bool found = false;

    snprintf(dir_path, sizeof(dir_path), "/proc/%ld/fd", (long)pid);
    dir = opendir(dir_path);
    if (dir == NULL) {
        return false;
    }
    while ((entry = readdir(dir)) != NULL) {
        char fd_path[PATH_MAX];
        char target[PATH_MAX];

        if (entry->d_name[0] == '.') {
            continue;
        }
        snprintf(fd_path, sizeof(fd_path), "%s/%s", dir_path, entry->d_name);
        if (d_handoff_readlink(fd_path, target, sizeof(target)) == 0 &&
            d_handoff_path_is_drm_target(target)) {
            found = true;
            break;
        }
    }
    closedir(dir);
    return found;
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

static int d_handoff_stop_drm_owner(const char *tag, pid_t pid);

struct dpublic_hud_service_opts {
    const char *intent_path;
    const char *pid_path;
    const char *status_path;
    bool release_drm;
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

static int dpublic_hud_service_mount_shared_run_dir(void) {
    int mounted;

    mounted = d3_path_is_mounted(A90_DPUBLIC_HUD_RUN_DIR);
    if (mounted < 0) {
        return mounted;
    }
    if (mounted) {
        a90_console_printf("%s shared_run_dir=already-mounted path=%s\r\n",
                           A90_DPUBLIC_HUD_SERVICE_SHARED_TAG,
                           A90_DPUBLIC_HUD_RUN_DIR);
        return 0;
    }
    if (mount("a90-dpublic-hud",
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
                                          const char *status_path) {
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
    (void)dpublic_hud_service_write_status(status_path, "running", getpid(), 0, 0);

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

static int dpublic_hud_service_start(const struct dpublic_hud_service_opts *opts) {
    pid_t existing;
    pid_t pid;
    int rc;

    rc = dpublic_hud_service_prepare_run_dir();
    a90_console_printf("%s start.run_dir=%s owner=root:a90hud mode=1770 rc=%d\r\n",
                       A90_DPUBLIC_HUD_SERVICE_TAG, A90_DPUBLIC_HUD_RUN_DIR, rc);
    if (rc < 0) {
        return rc;
    }
    if (dpublic_hud_service_read_pid(opts->pid_path, &existing) == 0 &&
        d_handoff_pid_alive(existing)) {
        a90_console_printf("%s start.already_running=1 pid=%ld\r\n",
                           A90_DPUBLIC_HUD_SERVICE_TAG, (long)existing);
        return -EBUSY;
    }

    rc = a90_service_stop(A90_SERVICE_HUD, A90_D_HANDOFF_HUD_TIMEOUT_MS);
    a90_console_printf("%s start.autohud_stop_rc=%d\r\n", A90_DPUBLIC_HUD_SERVICE_TAG, rc);
    if (rc < 0) {
        return rc;
    }

    pid = fork();
    if (pid < 0) {
        rc = -errno;
        a90_console_printf("%s start.fork_rc=%d\r\n", A90_DPUBLIC_HUD_SERVICE_TAG, rc);
        return rc;
    }
    if (pid == 0) {
        (void)setsid();
        _exit(dpublic_hud_service_child_loop(opts->intent_path, opts->status_path) == 0 ? 0 : 1);
    }

    rc = dpublic_hud_service_write_pid(opts->pid_path, pid);
    a90_console_printf("%s start.intent=%s\r\n", A90_DPUBLIC_HUD_SERVICE_TAG, opts->intent_path);
    a90_console_printf("%s start.pid=%ld\r\n", A90_DPUBLIC_HUD_SERVICE_TAG, (long)pid);
    a90_console_printf("%s start.pidfile=%s rc=%d\r\n",
                       A90_DPUBLIC_HUD_SERVICE_TAG, opts->pid_path, rc);
    if (rc < 0) {
        (void)kill(pid, SIGTERM);
        return rc;
    }
    a90_console_printf("%s start.process_model=forked-native-child-survives-switch-root\r\n",
                       A90_DPUBLIC_HUD_SERVICE_TAG);
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
    return running ? 0 : -ESRCH;
}

static int dpublic_hud_service_stop(const struct dpublic_hud_service_opts *opts) {
    pid_t pid;
    int rc = dpublic_hud_service_read_pid(opts->pid_path, &pid);

    if (rc < 0) {
        a90_console_printf("%s stop.not_running=1 rc=%d\r\n",
                           A90_DPUBLIC_HUD_SERVICE_TAG, rc);
        (void)unlink(opts->pid_path);
        return 0;
    }
    a90_console_printf("%s stop.pid=%ld release_drm=%d\r\n",
                       A90_DPUBLIC_HUD_SERVICE_TAG, (long)pid, opts->release_drm ? 1 : 0);
    rc = d_handoff_stop_drm_owner(A90_DPUBLIC_HUD_SERVICE_TAG, pid);
    (void)unlink(opts->pid_path);
    if (rc == 0) {
        (void)dpublic_hud_service_write_status(opts->status_path, "stopped", pid, 0, 0);
        a90_console_printf("%s stop.done=1\r\n", A90_DPUBLIC_HUD_SERVICE_TAG);
    } else {
        a90_console_printf("%s stop.done=0 rc=%d\r\n", A90_DPUBLIC_HUD_SERVICE_TAG, rc);
    }
    return rc;
}

int a90_server_distro_dpublic_hud_presenter_service_cmd(char **argv, int argc) {
    const char *mode;
    struct dpublic_hud_service_opts opts;
    int rc;

    if (argc < 2) {
        a90_console_printf("usage: dpublic-hud-presenter-service [start|status|stop] [options]\r\n");
        return -EINVAL;
    }
    mode = argv[1];
    rc = dpublic_hud_service_parse_opts(argv, argc, 2, &opts);
    if (rc < 0) {
        a90_console_printf("usage: dpublic-hud-presenter-service [start|status|stop] [options]\r\n");
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
    if (strcmp(mode, "start") == 0) {
        return dpublic_hud_service_start(&opts);
    }
    if (strcmp(mode, "status") == 0) {
        return dpublic_hud_service_status(&opts);
    }
    if (strcmp(mode, "stop") == 0) {
        return dpublic_hud_service_stop(&opts);
    }

    a90_console_printf("%s refused=unknown-mode mode=%s\r\n",
                       A90_DPUBLIC_HUD_SERVICE_TAG, mode);
    return -EINVAL;
}

static int d_handoff_stop_drm_owner(const char *tag, pid_t pid) {
    int rc;

    a90_console_printf("%s handoff_display drm_owner_pid=%ld action=term\r\n", tag, (long)pid);
    if (kill(pid, SIGTERM) < 0 && errno != ESRCH) {
        rc = -errno;
        a90_console_printf("%s handoff_display drm_owner_pid=%ld term_rc=%d\r\n",
                           tag, (long)pid, rc);
        return rc;
    }
    rc = d_handoff_wait_pid_gone(pid, A90_D_HANDOFF_DRM_OWNER_TIMEOUT_MS);
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
    rc = d_handoff_wait_pid_gone(pid, A90_D_HANDOFF_DRM_OWNER_TIMEOUT_MS);
    if (rc < 0) {
        a90_console_printf("%s handoff_display drm_owner_pid=%ld stop_rc=%d\r\n",
                           tag, (long)pid, rc);
    }
    return rc;
}

static int d_handoff_stop_display_owners(const char *tag) {
    DIR *proc;
    struct dirent *entry;
    unsigned int killed = 0;
    int final_rc = 0;
    int service_rc;

    service_rc = a90_service_stop(A90_SERVICE_HUD, A90_D_HANDOFF_HUD_TIMEOUT_MS);
    a90_console_printf("%s handoff_display service=autohud stop_rc=%d\r\n", tag, service_rc);
    if (service_rc < 0) {
        final_rc = service_rc;
    }

    proc = opendir("/proc");
    if (proc == NULL) {
        final_rc = final_rc < 0 ? final_rc : -errno;
        a90_console_printf("%s handoff_display scan=fail rc=%d\r\n", tag, final_rc);
        return final_rc;
    }
    while ((entry = readdir(proc)) != NULL) {
        pid_t pid;
        int rc;

        if (d_handoff_parse_pid(entry->d_name, &pid) < 0) {
            continue;
        }
        if (!d_handoff_pid_is_native_init(pid) || !d_handoff_pid_has_drm_fd(pid)) {
            continue;
        }
        if (dpublic_hud_service_pid_is_default(pid)) {
            a90_console_printf("%s handoff_display drm_owner_pid=%ld action=preserve-dpublic-hud-presenter\r\n",
                               tag, (long)pid);
            continue;
        }
        rc = d_handoff_stop_drm_owner(tag, pid);
        if (rc < 0) {
            final_rc = rc;
        } else {
            killed++;
        }
    }
    closedir(proc);

    a90_console_printf("%s handoff_display=done killed=%u rc=%d\r\n",
                       tag, killed, final_rc);
    return final_rc;
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

static int d3_regular_file_ok(const char *path) {
    int fd;
    struct stat st;
    int saved_errno;

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
    close(fd);
    if (!S_ISREG(st.st_mode) || st.st_size <= 0) {
        a90_console_printf("%s stop=not-regular-or-empty path=%s\r\n", A90_D3_TAG, path);
        return -EINVAL;
    }
    return 0;
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

static int d3_attach_loop(const char *image, bool *attached_out) {
    char *const argv[] = {
        (char *)A90_D3_BUSYBOX,
        (char *)"losetup",
        (char *)A90_D3_LOOP,
        (char *)image,
        NULL,
    };
    int rc = d3_run_busybox(argv, A90_D3_SWITCH_TIMEOUT_MS);

    if (rc != 0) {
        a90_console_printf("%s losetup=fail rc=%d\r\n", A90_D3_TAG, rc);
        return rc > 0 ? -EIO : rc;
    }
    if (attached_out != NULL) {
        *attached_out = true;
    }
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
        (char *)"rw",
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

static int d3_join(char *out, size_t out_size, const char *root, const char *leaf) {
    int n = snprintf(out, out_size, "%s/%s", root, leaf);

    if (n < 0 || (size_t)n >= out_size) {
        return -ENAMETOOLONG;
    }
    return 0;
}

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
    int rc;

    if (mounted_devpts != NULL) {
        *mounted_devpts = false;
    }
    rc = d3_join(dev_dir, sizeof(dev_dir), A90_D3_ROOT, "dev");
    if (rc < 0) {
        return rc;
    }
    rc = d3_mkdir_p(dev_dir, 0755);
    if (rc < 0) {
        return rc;
    }
    rc = d3_prepare_dev_node("dev/console", 0600, 5, 1);
    if (rc < 0) {
        return rc;
    }
    rc = d3_prepare_dev_node("dev/tty", 0666, 5, 0);
    if (rc < 0) {
        return rc;
    }
    rc = d3_prepare_dev_node("dev/ptmx", 0666, 5, 2);
    if (rc < 0) {
        return rc;
    }
    rc = d3_prepare_dev_node("dev/null", 0666, 1, 3);
    if (rc < 0) {
        return rc;
    }
    rc = d3_prepare_dev_node("dev/zero", 0666, 1, 5);
    if (rc < 0) {
        return rc;
    }
    rc = d3_prepare_dev_node("dev/random", 0666, 1, 8);
    if (rc < 0) {
        return rc;
    }
    rc = d3_prepare_dev_node("dev/urandom", 0666, 1, 9);
    if (rc < 0) {
        return rc;
    }
    rc = d3_prepare_optional_ttygs0();
    if (rc < 0) {
        return rc;
    }
    rc = d3_join(pts_dir, sizeof(pts_dir), A90_D3_ROOT, "dev/pts");
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
        a90_console_printf("%s devpts=mounted path=%s\r\n", A90_D3_TAG, pts_dir);
    } else {
        a90_console_printf("%s devpts=warn rc=-%d (%s)\r\n",
                           A90_D3_TAG, errno, strerror(errno));
    }
    a90_console_printf("%s dev_mountpoint=0 dev_nodes=prepared root=%s\r\n",
                       A90_D3_TAG, dev_dir);
    return 0;
}

static void d3_restore_mount_one(const char *leaf, const char *dst) {
    char src[PATH_MAX];

    if (d3_join(src, sizeof(src), A90_D3_ROOT, leaf) < 0) {
        return;
    }
    (void)mount(src, dst, NULL, MS_MOVE, NULL);
}

static void d3_unmount_leaf(const char *leaf) {
    char path[PATH_MAX];

    if (d3_join(path, sizeof(path), A90_D3_ROOT, leaf) < 0) {
        return;
    }
    (void)umount2(path, MNT_DETACH);
}

static int d3_move_core_mounts(bool *moved_proc,
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
    rc = d3_move_mount_one("/proc", "proc");
    if (rc < 0) {
        return rc;
    }
    if (moved_proc != NULL) {
        *moved_proc = true;
    }
    rc = d3_move_mount_one("/sys", "sys");
    if (rc < 0) {
        d3_restore_mount_one("proc", "/proc");
        return rc;
    }
    if (moved_sys != NULL) {
        *moved_sys = true;
    }
    if (dev_mounted) {
        rc = d3_move_mount_one("/dev", "dev");
        if (rc < 0) {
            d3_restore_mount_one("sys", "/sys");
            d3_restore_mount_one("proc", "/proc");
            return rc;
        }
        if (moved_dev != NULL) {
            *moved_dev = true;
        }
    } else {
        rc = d3_prepare_new_dev(mounted_devpts);
        if (rc < 0) {
            d3_restore_mount_one("sys", "/sys");
            d3_restore_mount_one("proc", "/proc");
            return rc;
        }
    }
    return 0;
}

static void d3_restore_core_mounts(bool moved_proc, bool moved_sys, bool moved_dev, bool mounted_devpts) {
    if (mounted_devpts) {
        d3_unmount_leaf("dev/pts");
    }
    if (moved_dev) {
        d3_restore_mount_one("dev", "/dev");
    }
    if (moved_sys) {
        d3_restore_mount_one("sys", "/sys");
    }
    if (moved_proc) {
        d3_restore_mount_one("proc", "/proc");
    }
}

int a90_server_distro_switch_root_cmd(char **argv, int argc) {
    const char *image;
    const char *expected_sha;
    char actual_sha[65];
    int rc;
    bool loop_created = false;
    bool loop_attached = false;
    bool root_mounted = false;
    bool moved_proc = false;
    bool moved_sys = false;
    bool moved_dev = false;
    bool mounted_devpts = false;
    int mounted;
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
    rc = d3_regular_file_ok(image);
    if (rc < 0) {
        return rc;
    }
    if (a90_helper_sha256_file(image, actual_sha, sizeof(actual_sha)) != 0) {
        a90_console_printf("%s sha=compute-fail\r\n", A90_D3_TAG);
        return -EIO;
    }
    if (!d3_sha_equal_ci(actual_sha, expected_sha)) {
        a90_console_printf("%s sha=%s expected_sha_match=0 stop=sha-mismatch\r\n",
                           A90_D3_TAG, actual_sha);
        return -EPERM;
    }
    a90_console_printf("%s sha=%s expected_sha_match=1\r\n", A90_D3_TAG, actual_sha);

    rc = d3_mkdir_p(A90_D3_ROOT, 0755);
    if (rc < 0) {
        a90_console_printf("%s mkdir_root=fail rc=%d root=%s\r\n", A90_D3_TAG, rc, A90_D3_ROOT);
        return rc;
    }
    mounted = d3_path_is_mounted(A90_D3_ROOT);
    if (mounted < 0) {
        return mounted;
    }
    if (mounted) {
        a90_console_printf("%s stop=root-already-mounted root=%s\r\n", A90_D3_TAG, A90_D3_ROOT);
        return -EBUSY;
    }
    rc = d3_ensure_loop_node(&loop_created);
    if (rc < 0) {
        a90_console_printf("%s loop_node=fail rc=%d\r\n", A90_D3_TAG, rc);
        return rc;
    }
    rc = d3_attach_loop(image, &loop_attached);
    if (rc < 0) {
        goto fail_before_move;
    }
    rc = d3_mount_root();
    if (rc < 0) {
        goto fail_before_move;
    }
    root_mounted = true;
    rc = d3_check_distro_init();
    if (rc < 0) {
        a90_console_printf("%s stop=distro-init-invalid rc=%d\r\n", A90_D3_TAG, rc);
        goto fail_before_move;
    }
    rc = d_handoff_stop_display_owners(A90_D3_TAG);
    if (rc < 0) {
        a90_console_printf("%s stop=handoff-display-owner rc=%d\r\n", A90_D3_TAG, rc);
        goto fail_before_move;
    }
    rc = d3_move_core_mounts(&moved_proc, &moved_sys, &moved_dev, &mounted_devpts);
    if (rc < 0) {
        a90_console_printf("%s mount_move=fail rc=%d\r\n", A90_D3_TAG, rc);
        goto fail_before_move;
    }

    a90_console_printf("%s exec_switch_root_now busybox=%s root=%s init=%s console=reuse-stdio\r\n",
                       A90_D3_TAG, A90_D3_BUSYBOX, A90_D3_ROOT, A90_D3_INIT);
    a90_logf("server-distro", "D3 switch_root exec image=%s root=%s", image, A90_D3_ROOT);
    sync();
    usleep(200000);
    execve(A90_D3_BUSYBOX, switch_argv, newenv);

    rc = -errno;
    a90_console_printf("%s execve_switch_root=fail rc=%d errno=%d (%s)\r\n",
                       A90_D3_TAG, rc, -rc, strerror(-rc));
    d3_restore_core_mounts(moved_proc, moved_sys, moved_dev, mounted_devpts);
    return rc;

fail_before_move:
    if (root_mounted) {
        if (umount2(A90_D3_ROOT, MNT_DETACH) == 0) {
            a90_console_printf("%s rootfs=unmounted-after-fail root=%s\r\n",
                               A90_D3_TAG, A90_D3_ROOT);
        }
    }
    if (loop_attached) {
        (void)d3_detach_loop();
    }
    if (loop_created) {
        (void)unlink(A90_D3_LOOP);
    }
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
#define A90_D4_EXT_FEATURE_COMPAT_OFFSET 1116
#define A90_D4_EXT_COMPAT_HAS_JOURNAL 0x00000004U

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

static int d4_dpublic_hud_bind_target(char *out, size_t out_size) {
    return d4_join_root(out, out_size, "run/a90-dpublic");
}

static void d4_unbind_dpublic_hud_run_dir(void) {
    char dst[PATH_MAX];

    if (d4_dpublic_hud_bind_target(dst, sizeof(dst)) < 0) {
        return;
    }
    (void)umount2(dst, MNT_DETACH);
}

static int d4_bind_dpublic_hud_run_dir(bool *bound_out) {
    char dst[PATH_MAX];
    struct stat src_st;
    struct stat dst_st;
    int mounted;
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
    (void)chown(dst, 0, A90_DPUBLIC_HUD_GROUP_GID);
    (void)chmod(dst, A90_DPUBLIC_HUD_RUN_DIR_MODE);
    if (bound_out != NULL) {
        *bound_out = true;
    }
    if (stat(A90_DPUBLIC_HUD_RUN_DIR, &src_st) == 0 && stat(dst, &dst_st) == 0) {
        a90_console_printf("%s shared_run_bind=ok source=%s target=%s same_dev=%d same_ino=%d\r\n",
                           A90_DPUBLIC_HUD_SERVICE_SHARED_TAG,
                           A90_DPUBLIC_HUD_RUN_DIR,
                           dst,
                           src_st.st_dev == dst_st.st_dev ? 1 : 0,
                           src_st.st_ino == dst_st.st_ino ? 1 : 0);
    } else {
        a90_console_printf("%s shared_run_bind=ok source=%s target=%s\r\n",
                           A90_DPUBLIC_HUD_SERVICE_SHARED_TAG,
                           A90_DPUBLIC_HUD_RUN_DIR,
                           dst);
    }
    return 0;
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
