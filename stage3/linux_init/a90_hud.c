#include "a90_hud.h"

#include <errno.h>
#include <fcntl.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#include "a90_config.h"
#include "a90_draw.h"
#include "a90_log.h"
#include "a90_timeline.h"
#include "a90_util.h"

#ifndef O_CLOEXEC
#define O_CLOEXEC 0
#endif

#ifndef O_NOFOLLOW
#define O_NOFOLLOW 0
#endif

static bool hud_read_key_value_file(const char *path,
                                    const char *key,
                                    char *out,
                                    size_t out_size) {
    FILE *fp;
    char line[192];
    size_t key_len;

    if (out_size == 0) {
        return false;
    }
    out[0] = '\0';
    fp = fopen(path, "r");
    if (fp == NULL) {
        return false;
    }
    key_len = strlen(key);
    while (fgets(line, sizeof(line), fp) != NULL) {
        size_t len;

        if (strncmp(line, key, key_len) != 0) {
            continue;
        }
        len = strlen(line);
        while (len > key_len && (line[len - 1] == '\n' || line[len - 1] == '\r')) {
            line[--len] = '\0';
        }
        snprintf(out, out_size, "%s", line + key_len);
        fclose(fp);
        return true;
    }
    fclose(fp);
    return false;
}

static void hud_append_wifi_token(char *out, size_t out_size, const char *fmt, ...) {
    va_list ap;
    size_t len;

    if (out_size == 0) {
        return;
    }
    len = strlen(out);
    if (len >= out_size - 1) {
        return;
    }
    va_start(ap, fmt);
    (void)vsnprintf(out + len, out_size - len, fmt, ap);
    va_end(ap);
}

static void hud_read_wifi_line(char *out, size_t out_size, uint32_t *color_out) {
    static const char *summary_path = "/cache/native-init-wifi-test-boot-v726.summary";
    static const char *runtime_path = "/cache/native-init-wifi-runtime.summary";
    struct stat st;
    char operstate[32] = "?";
    char carrier[16] = "?";
    char mac[32] = "?";
    char runtime_present[16] = "";
    char runtime_operstate[32] = "";
    char runtime_carrier[16] = "";
    char runtime_mac[32] = "";
    char ssid_label[64] = "";
    char rssi_dbm[24] = "";
    char linkspeed_mbps[24] = "";
    char ip4_label[32] = "";
    char rx_mbps[24] = "";
    char tx_mbps[24] = "";
    char baseline_ready[16] = "0";
    char supervisor_result[48] = "";
    bool wlan0_present;
    bool link_up;
    bool ready;

    if (out_size == 0) {
        return;
    }
    out[0] = '\0';
    if (color_out != NULL) {
        *color_out = 0xffcc33;
    }

    wlan0_present = (lstat("/sys/class/net/wlan0", &st) == 0);
    (void)hud_read_key_value_file(summary_path,
                                  "baseline_ready=",
                                  baseline_ready,
                                  sizeof(baseline_ready));
    (void)hud_read_key_value_file(summary_path,
                                  "supervisor_result=",
                                  supervisor_result,
                                  sizeof(supervisor_result));
    if (hud_read_key_value_file(runtime_path,
                                "wlan0_present=",
                                runtime_present,
                                sizeof(runtime_present))) {
        (void)hud_read_key_value_file(runtime_path,
                                      "operstate=",
                                      runtime_operstate,
                                      sizeof(runtime_operstate));
        (void)hud_read_key_value_file(runtime_path,
                                      "carrier=",
                                      runtime_carrier,
                                      sizeof(runtime_carrier));
        (void)hud_read_key_value_file(runtime_path,
                                      "mac_label=",
                                      runtime_mac,
                                      sizeof(runtime_mac));
        (void)hud_read_key_value_file(runtime_path,
                                      "ssid_label=",
                                      ssid_label,
                                      sizeof(ssid_label));
        (void)hud_read_key_value_file(runtime_path,
                                      "rssi_dbm=",
                                      rssi_dbm,
                                      sizeof(rssi_dbm));
        (void)hud_read_key_value_file(runtime_path,
                                      "linkspeed_mbps=",
                                      linkspeed_mbps,
                                      sizeof(linkspeed_mbps));
        (void)hud_read_key_value_file(runtime_path,
                                      "ip4_label=",
                                      ip4_label,
                                      sizeof(ip4_label));
        (void)hud_read_key_value_file(runtime_path,
                                      "rx_mbps=",
                                      rx_mbps,
                                      sizeof(rx_mbps));
        (void)hud_read_key_value_file(runtime_path,
                                      "tx_mbps=",
                                      tx_mbps,
                                      sizeof(tx_mbps));
    }

    if (!wlan0_present) {
        if (supervisor_result[0] != '\0') {
            snprintf(out, out_size, "WIFI WAIT %.40s", supervisor_result);
        } else {
            snprintf(out, out_size, "WIFI WAIT wlan0 missing");
        }
        return;
    }

    if (read_trimmed_text_file("/sys/class/net/wlan0/operstate",
                               operstate,
                               sizeof(operstate)) < 0) {
        snprintf(operstate, sizeof(operstate), "?");
    }
    if (read_trimmed_text_file("/sys/class/net/wlan0/carrier",
                               carrier,
                               sizeof(carrier)) < 0) {
        snprintf(carrier, sizeof(carrier), "no-carrier");
    }
    if (read_trimmed_text_file("/sys/class/net/wlan0/address",
                               mac,
                               sizeof(mac)) < 0) {
        snprintf(mac, sizeof(mac), "?");
    }

    if (runtime_operstate[0] != '\0') {
        snprintf(operstate, sizeof(operstate), "%s", runtime_operstate);
    }
    if (runtime_carrier[0] != '\0') {
        snprintf(carrier, sizeof(carrier), "%s", runtime_carrier);
    }
    if (runtime_mac[0] != '\0') {
        snprintf(mac, sizeof(mac), "%s", runtime_mac);
    }

    link_up = strcmp(carrier, "1") == 0 || strcmp(operstate, "up") == 0;
    ready = strcmp(baseline_ready, "1") == 0;
    if (link_up) {
        snprintf(out,
                 out_size,
                 "WIFI UP %.32s",
                 ssid_label[0] != '\0' ? ssid_label : "wlan0");
        if (rssi_dbm[0] != '\0') {
            hud_append_wifi_token(out, out_size, " %sdBm", rssi_dbm);
        }
        if (linkspeed_mbps[0] != '\0') {
            hud_append_wifi_token(out, out_size, " %sM", linkspeed_mbps);
        }
        if (ip4_label[0] != '\0' && strcmp(ip4_label, "none") != 0) {
            hud_append_wifi_token(out, out_size, " %s", ip4_label);
        }
        if (rx_mbps[0] != '\0' && tx_mbps[0] != '\0' &&
            (strcmp(rx_mbps, "0.0") != 0 || strcmp(tx_mbps, "0.0") != 0)) {
            hud_append_wifi_token(out, out_size, " D%s/U%sM", rx_mbps, tx_mbps);
        }
        if (color_out != NULL) {
            *color_out = 0x88ee88;
        }
    } else if (ready) {
        snprintf(out, out_size, "WIFI READY wlan0 %s %.17s", operstate, mac);
        if (color_out != NULL) {
            *color_out = 0x88ee88;
        }
    } else {
        snprintf(out, out_size, "WIFI IFACE wlan0 %s %.17s", operstate, mac);
        if (color_out != NULL) {
            *color_out = 0xffcc33;
        }
    }
}

static char boot_splash_lines[BOOT_SPLASH_LINE_COUNT][BOOT_SPLASH_LINE_MAX] = {
    "[ KERNEL ] STOCK LINUX 4.14",
    "[ CACHE  ] WAITING",
    "[ SD     ] WAITING",
    "[ STORAGE] CACHE FALLBACK",
    "[ SERIAL ] USB ACM STARTING",
    "[ RUNTIME] HUD MENU LOADING",
};

static uint32_t boot_splash_line_color(const char *line) {
    if (strstr(line, "FAIL") != NULL ||
        strstr(line, "ERR") != NULL ||
        strstr(line, "MISMATCH") != NULL) {
        return 0xff6666;
    }
    if (strstr(line, "WARN") != NULL ||
        strstr(line, "FALLBACK") != NULL) {
        return 0xffcc33;
    }
    if (strstr(line, "OK") != NULL ||
        strstr(line, "READY") != NULL ||
        strstr(line, "MAIN") != NULL) {
        return 0x88ee88;
    }
    return 0xffffff;
}

void a90_hud_boot_splash_set_line(size_t index, const char *fmt, ...) {
    va_list ap;

    if (index >= BOOT_SPLASH_LINE_COUNT) {
        return;
    }
    va_start(ap, fmt);
    vsnprintf(boot_splash_lines[index], sizeof(boot_splash_lines[index]), fmt, ap);
    va_end(ap);
}

void a90_hud_draw_boot_splash(struct a90_fb *fb) {
    uint32_t width = fb->width;
    uint32_t height = fb->height;
    uint32_t scale = width >= 1080 ? 5 : 4;
    uint32_t title_scale = scale + 2;
    uint32_t x = width / 16;
    uint32_t y = height / 8;
    uint32_t card_w = width - x * 2;
    uint32_t line_h = scale * 11;
    uint32_t card_y;
    uint32_t row_y;
    uint32_t row_gap = scale * 12;
    uint32_t row_x;
    uint32_t row_w;
    uint32_t footer_scale = scale > 3 ? scale - 1 : scale;
    size_t index;

    if (x < scale * 10) {
        x = scale * 10;
    }
    card_w = width - x * 2;

    a90_draw_clear(fb, 0x020713);
    a90_draw_rect(fb, 0, 0, width, height / 36, 0x0b2a55);
    a90_draw_rect(fb, 0, height - height / 60, width, height / 60, 0x0088cc);
    a90_draw_rect(fb, x, y - scale * 3, card_w, scale * 2, 0x0088cc);

    a90_draw_text_fit(fb, x, y, "A90 NATIVE INIT", 0xffffff, title_scale, card_w);
    y += title_scale * 10;
    a90_draw_text_fit(fb, x, y, INIT_BANNER, 0xffcc33, scale, card_w);
    y += line_h;
    a90_draw_text_fit(fb, x, y, INIT_CREATOR, 0x88ee88, scale, card_w);

    card_y = y + line_h + scale * 5;
    a90_draw_rect(fb,
                  x - scale,
                  card_y - scale,
                  card_w,
                  row_gap * BOOT_SPLASH_LINE_COUNT + scale * 2,
                  0x101820);
    a90_draw_rect(fb,
                  x - scale,
                  card_y - scale,
                  scale * 2,
                  row_gap * BOOT_SPLASH_LINE_COUNT + scale * 2,
                  0xffcc33);

    row_y = card_y + scale;
    row_x = x + scale * 4;
    row_w = width - row_x - x;
    for (index = 0; index < BOOT_SPLASH_LINE_COUNT; ++index) {
        a90_draw_text_fit(fb,
                          row_x,
                          row_y + row_gap * (uint32_t)index,
                          boot_splash_lines[index],
                          boot_splash_line_color(boot_splash_lines[index]),
                          scale,
                          row_w);
    }

    a90_draw_text_fit(fb,
                      x,
                      height - footer_scale * 16,
                      "VOL KEYS OPEN MENU AFTER BOOT",
                      0xbbbbbb,
                      footer_scale,
                      card_w);
}

void a90_hud_draw_status_overlay(struct a90_fb *fb,
                                 const struct a90_hud_storage_status *storage,
                                 unsigned int refresh_sec,
                                 unsigned int sequence) {
    struct a90_metrics_snapshot snapshot;
    char boot_summary[64];
    char bat_tag[8];
    char footer[64];
    char storage_line[96];
    char wifi_line[96];
    const char *warning = storage != NULL && storage->warning != NULL ? storage->warning : "";
    const char *backend = storage != NULL && storage->backend != NULL ? storage->backend : "?";
    const char *root = storage != NULL && storage->root != NULL ? storage->root : "?";
    uint32_t scale = 5;
    uint32_t x = fb->width / 24;
    uint32_t line_h = scale * 10;
    uint32_t card_h = line_h + scale * 4;
    uint32_t card_w = fb->width - (x * 2);
    uint32_t footer_y = fb->height - (line_h * 4);
    uint32_t footer_scale = scale;
    uint32_t footer_text_y = footer_y;
    uint32_t char_w = scale * 6;
    uint32_t glyph_h = scale * 7;
    uint32_t y = fb->height / 16;
    uint32_t slot = line_h + scale * 3;
    uint32_t bat_color;
    uint32_t boot_color;
    uint32_t storage_color;
    uint32_t wifi_color;
    uint32_t off;
    long bat_pct_val;

    (void)refresh_sec;
    (void)sequence;

    if (y > glyph_h + glyph_h / 2 + scale * 2)
        y -= glyph_h + glyph_h / 2;

    a90_metrics_read_snapshot(&snapshot);
    a90_timeline_boot_summary(boot_summary, sizeof(boot_summary));

    bat_tag[0] = '\0';
    if (strncmp(snapshot.battery_status, "Charging", 8) == 0)
        strncpy(bat_tag, "CHG", sizeof(bat_tag) - 1);
    else if (strncmp(snapshot.battery_status, "Full", 4) == 0)
        strncpy(bat_tag, "FUL", sizeof(bat_tag) - 1);
    else if (strncmp(snapshot.battery_status, "Discharging", 11) == 0)
        strncpy(bat_tag, "DSC", sizeof(bat_tag) - 1);
    bat_tag[sizeof(bat_tag) - 1] = '\0';

    bat_pct_val = atol(snapshot.battery_pct);
    if (bat_pct_val <= 20)
        bat_color = 0xff4444;
    else if (bat_pct_val <= 50)
        bat_color = 0xffcc33;
    else
        bat_color = 0x88ee88;

    boot_color = (strncmp(boot_summary, "BOOT OK", 7) == 0) ? 0x88ee88 : 0xff6666;

    snprintf(footer, sizeof(footer), "A90 %s %s UP %.8s",
             INIT_VERSION,
             INIT_BUILD,
             snapshot.uptime);
    while (footer_scale > 1 &&
           x + (uint32_t)strlen(footer) * footer_scale * 6 > fb->width - x)
        --footer_scale;
    if (footer_scale < scale)
        footer_text_y += ((scale - footer_scale) * 7) / 2;

    a90_draw_rect(fb, x - scale, y + slot * 0 - scale, card_w, card_h, 0x202020);
    a90_draw_rect(fb, x - scale, y + slot * 1 - scale, card_w, card_h, 0x202020);
    a90_draw_rect(fb, x - scale, y + slot * 2 - scale, card_w, card_h, 0x202020);
    a90_draw_rect(fb, x - scale, y + slot * 3 - scale, card_w, card_h, 0x202020);
    a90_draw_rect(fb, x - scale, y + slot * 4 - scale, card_w, card_h, 0x202020);

    a90_draw_text(fb, x, y + slot * 0, "A90 INIT ", 0x909090, scale);
    a90_draw_text(fb, x + 9 * char_w, y + slot * 0, boot_summary, boot_color, scale);

    off = 0;
    a90_draw_text(fb, x + off * char_w, y + slot * 1, "BAT ", 0x909090, scale); off += 4;
    a90_draw_text(fb, x + off * char_w, y + slot * 1, snapshot.battery_pct, bat_color, scale);
    off += (uint32_t)strlen(snapshot.battery_pct) + 1;
    if (bat_tag[0] != '\0') {
        a90_draw_text(fb, x + off * char_w, y + slot * 1, bat_tag, bat_color, scale);
        off += 4;
    }
    a90_draw_text(fb, x + off * char_w, y + slot * 1, "PWR ", 0x909090, scale); off += 4;
    a90_draw_text(fb, x + off * char_w, y + slot * 1, snapshot.power_now, 0xffffff, scale);
    off += (uint32_t)strlen(snapshot.power_now) + 1;
    a90_draw_text(fb, x + off * char_w, y + slot * 1, "AVG ", 0x909090, scale); off += 4;
    a90_draw_text(fb, x + off * char_w, y + slot * 1, snapshot.power_avg, 0xffffff, scale);

    off = 0;
    a90_draw_text(fb, x + off * char_w, y + slot * 2, "CPU ", 0x909090, scale); off += 4;
    a90_draw_text(fb, x + off * char_w, y + slot * 2, snapshot.cpu_temp, 0xffffff, scale);
    off += (uint32_t)strlen(snapshot.cpu_temp) + 1;
    a90_draw_text(fb, x + off * char_w, y + slot * 2, snapshot.cpu_usage, 0xffffff, scale);
    off += (uint32_t)strlen(snapshot.cpu_usage) + 1;
    a90_draw_text(fb, x + off * char_w, y + slot * 2, "GPU ", 0x909090, scale); off += 4;
    a90_draw_text(fb, x + off * char_w, y + slot * 2, snapshot.gpu_temp, 0xffffff, scale);
    off += (uint32_t)strlen(snapshot.gpu_temp) + 1;
    a90_draw_text(fb, x + off * char_w, y + slot * 2, snapshot.gpu_usage, 0xffffff, scale);

    off = 0;
    a90_draw_text(fb, x + off * char_w, y + slot * 3, "MEM ", 0x909090, scale); off += 4;
    a90_draw_text(fb, x + off * char_w, y + slot * 3, snapshot.memory, 0xffffff, scale);
    off += (uint32_t)strlen(snapshot.memory) + 1;
    a90_draw_text(fb, x + off * char_w, y + slot * 3, "LOAD ", 0x909090, scale); off += 5;
    a90_draw_text(fb, x + off * char_w, y + slot * 3, snapshot.loadavg, 0xffffff, scale);

    hud_read_wifi_line(wifi_line, sizeof(wifi_line), &wifi_color);
    a90_draw_text_fit(fb,
                      x,
                      y + slot * 4,
                      wifi_line,
                      wifi_color,
                      scale > 3 ? scale - 2 : scale,
                      card_w - scale * 2);

    if (warning[0] != '\0') {
        snprintf(storage_line, sizeof(storage_line), "SD WARN %.70s", warning);
        storage_color = 0xffcc33;
    } else {
        snprintf(storage_line, sizeof(storage_line), "STORAGE %s %.60s", backend, root);
        storage_color = 0x88ee88;
    }
    storage_line[sizeof(storage_line) - 1] = '\0';
    a90_draw_text_fit(fb,
                      x,
                      y + slot * 5,
                      storage_line,
                      storage_color,
                      scale > 3 ? scale - 2 : scale,
                      card_w - scale * 2);

    a90_draw_text(fb, x, footer_text_y, footer, 0xbbbbbb, footer_scale);
}

int a90_hud_draw_status_frame(const struct a90_hud_storage_status *storage,
                              const char *label,
                              bool verbose) {
    if (a90_kms_begin_frame(0x000000) < 0) {
        return negative_errno_or(ENODEV);
    }
    a90_hud_draw_status_overlay(a90_kms_framebuffer(), storage, 0, 1);
    if (a90_kms_present(label, verbose) < 0) {
        return negative_errno_or(EIO);
    }
    return 0;
}

static int hud_read_log_tail(char lines[KMS_LOG_TAIL_MAX_LINES][KMS_LOG_TAIL_LINE_MAX],
                             int max_lines) {
    char ring[KMS_LOG_TAIL_MAX_LINES][KMS_LOG_TAIL_LINE_MAX];
    int index = 0;
    int count;
    int start;
    int i;
    FILE *fp;

    if (max_lines <= 0) {
        return 0;
    }
    if (max_lines > KMS_LOG_TAIL_MAX_LINES) {
        max_lines = KMS_LOG_TAIL_MAX_LINES;
    }

    fp = fopen(a90_log_path(), "r");
    if (fp == NULL) {
        return 0;
    }

    while (fgets(ring[index % max_lines], KMS_LOG_TAIL_LINE_MAX, fp) != NULL) {
        size_t len = strlen(ring[index % max_lines]);

        while (len > 0 &&
               (ring[index % max_lines][len - 1] == '\n' ||
                ring[index % max_lines][len - 1] == '\r')) {
            ring[index % max_lines][--len] = '\0';
        }
        if (len == 0) {
            continue;
        }
        ++index;
    }
    fclose(fp);

    count = index < max_lines ? index : max_lines;
    start = index >= max_lines ? index % max_lines : 0;
    for (i = 0; i < count; ++i) {
        snprintf(lines[i], KMS_LOG_TAIL_LINE_MAX, "%s",
                 ring[(start + i) % max_lines]);
    }
    return count;
}

static uint32_t hud_log_tail_line_color(const char *line) {
    if (strstr(line, "failed") != NULL ||
        strstr(line, " rc=-") != NULL ||
        strstr(line, " error=") != NULL) {
        return 0xff7777;
    }
    if (strstr(line, "cancel") != NULL ||
        strstr(line, "ignored") != NULL ||
        strstr(line, "busy") != NULL) {
        return 0xffcc33;
    }
    if (strstr(line, "input") != NULL ||
        strstr(line, "screenmenu") != NULL) {
        return 0x66ddff;
    }
    if (strstr(line, "boot") != NULL ||
        strstr(line, "timeline") != NULL) {
        return 0x88ee88;
    }
    return 0x808080;
}

static void hud_log_tail_next_chunk(const char *line,
                                    size_t offset,
                                    size_t max_chars,
                                    char *out,
                                    size_t out_size,
                                    size_t *next_offset) {
    size_t len = strlen(line + offset);
    size_t chunk_len;
    size_t split;

    if (out_size == 0) {
        *next_offset = offset;
        return;
    }
    if (max_chars == 0) {
        out[0] = '\0';
        *next_offset = offset;
        return;
    }

    if (len <= max_chars) {
        snprintf(out, out_size, "%s", line + offset);
        *next_offset = offset + len;
        return;
    }

    chunk_len = max_chars;
    split = chunk_len;
    while (split > 8 && line[offset + split] != ' ' && line[offset + split] != '\t') {
        --split;
    }
    if (split > 8) {
        chunk_len = split;
    }
    if (chunk_len >= out_size) {
        chunk_len = out_size - 1;
    }

    memcpy(out, line + offset, chunk_len);
    out[chunk_len] = '\0';
    offset += chunk_len;
    while (line[offset] == ' ' || line[offset] == '\t') {
        ++offset;
    }
    *next_offset = offset;
}

static int hud_log_tail_wrap_count(const char *line, size_t max_chars) {
    size_t offset = 0;
    int count = 0;

    if (max_chars == 0 || line[0] == '\0') {
        return 0;
    }
    while (line[offset] != '\0' && count < 16) {
        char chunk[KMS_LOG_TAIL_LINE_MAX];
        size_t next_offset;

        hud_log_tail_next_chunk(line,
                                offset,
                                max_chars,
                                chunk,
                                sizeof(chunk),
                                &next_offset);
        if (next_offset <= offset) {
            break;
        }
        offset = next_offset;
        ++count;
    }
    return count;
}

void a90_hud_draw_log_tail_panel(struct a90_fb *fb,
                                 uint32_t x,
                                 uint32_t y,
                                 uint32_t width,
                                 uint32_t bottom,
                                 int max_lines,
                                 const char *title,
                                 uint32_t scale) {
    char lines[KMS_LOG_TAIL_MAX_LINES][KMS_LOG_TAIL_LINE_MAX];
    uint32_t line_h;
    uint32_t title_h;
    uint32_t title_gap;
    uint32_t panel_h;
    uint32_t available;
    uint32_t text_width;
    size_t max_chars;
    int total;
    int row_budget;
    int visual_rows = 0;
    int start;
    int i;

    if (scale < 1) {
        scale = 1;
    }
    if (max_lines > KMS_LOG_TAIL_MAX_LINES) {
        max_lines = KMS_LOG_TAIL_MAX_LINES;
    }
    if (bottom <= y || width <= scale * 4) {
        return;
    }

    line_h = scale * 9;
    title_h = scale * 10;
    title_gap = scale * 3;
    text_width = width - scale * 2;
    max_chars = text_width / (scale * 6);
    if (max_chars < 8) {
        return;
    }
    if (max_chars >= KMS_LOG_TAIL_LINE_MAX) {
        max_chars = KMS_LOG_TAIL_LINE_MAX - 1;
    }
    available = bottom - y;
    if (available <= title_h + title_gap + scale * 4) {
        return;
    }

    row_budget = (int)((available - title_h - title_gap - scale * 4) / (line_h + 2));
    if (row_budget <= 0) {
        return;
    }

    total = hud_read_log_tail(lines, max_lines);
    if (total <= 0) {
        return;
    }

    start = total;
    while (start > 0) {
        int rows = hud_log_tail_wrap_count(lines[start - 1], max_chars);

        if (rows <= 0) {
            rows = 1;
        }
        if (visual_rows > 0 && visual_rows + rows > row_budget) {
            break;
        }
        if (visual_rows == 0 && rows > row_budget) {
            visual_rows = row_budget;
            --start;
            break;
        }
        visual_rows += rows;
        --start;
    }
    if (visual_rows <= 0) {
        return;
    }

    panel_h = title_h + title_gap + (uint32_t)visual_rows * (line_h + 2) + scale * 2;

    a90_draw_rect(fb, x - scale, y - scale, width, panel_h, 0x080808);
    a90_draw_rect(fb, x, y, width - scale * 2, 1, 0x303030);
    a90_draw_text_fit(fb, x, y + scale * 2, title, 0xffcc33, scale, width - scale * 2);
    y += title_h + title_gap;

    visual_rows = 0;
    for (i = start; i < total && visual_rows < row_budget; ++i) {
        const char *line = lines[i];
        size_t offset = 0;
        uint32_t color = hud_log_tail_line_color(line);

        while (line[offset] != '\0' && visual_rows < row_budget) {
            char chunk[KMS_LOG_TAIL_LINE_MAX];
            size_t next_offset;
            uint32_t row_y = y + (uint32_t)visual_rows * (line_h + 2);

            hud_log_tail_next_chunk(line,
                                    offset,
                                    max_chars,
                                    chunk,
                                    sizeof(chunk),
                                    &next_offset);
            a90_draw_text(fb, x, row_y, chunk, color, scale);
            offset = next_offset;
            ++visual_rows;
        }
    }
}

void a90_hud_draw_hud_log_tail(struct a90_fb *fb) {
    uint32_t scale = 3;
    uint32_t hud_scale = 5;
    uint32_t slot = (hud_scale * 10) + hud_scale * 3;
    uint32_t card_h = (hud_scale * 10) + hud_scale * 4;
    uint32_t glyph_h = hud_scale * 7;
    uint32_t x = fb->width / 24;
    uint32_t card_w = fb->width - x * 2;
    uint32_t y = fb->height / 16;
    uint32_t area_y;

    if (!a90_hud_log_tail_enabled()) {
        return;
    }

    if (y > glyph_h + glyph_h / 2 + hud_scale * 2)
        y -= glyph_h + glyph_h / 2;
    area_y = y + 3 * slot + card_h + hud_scale * 8;

    a90_hud_draw_log_tail_panel(fb,
                                x,
                                area_y,
                                card_w,
                                fb->height - hud_scale * 16,
                                24,
                                "LOG TAIL",
                                scale);
}

bool a90_hud_log_tail_enabled(void) {
    if (KMS_LOG_TAIL_DEFAULT_ENABLED) {
        return true;
    }
    return access(HUD_LOG_TAIL_ENABLE_PATH, F_OK) == 0;
}

int a90_hud_set_log_tail_enabled(bool enabled) {
    int fd;

    if (!enabled) {
        if (unlink(HUD_LOG_TAIL_ENABLE_PATH) < 0 && errno != ENOENT) {
            return negative_errno_or(EIO);
        }
        return 0;
    }

    fd = open(HUD_LOG_TAIL_ENABLE_PATH,
              O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC | O_NOFOLLOW,
              0600);
    if (fd < 0) {
        return negative_errno_or(EIO);
    }
    if (write_all_checked(fd, "enabled\n", 8) < 0) {
        int saved_errno = errno;
        close(fd);
        return -saved_errno;
    }
    close(fd);
    return 0;
}
