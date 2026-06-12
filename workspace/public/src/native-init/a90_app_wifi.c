#include "a90_app_wifi.h"

#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "a90_draw.h"
#include "a90_kms.h"
#include "a90_util.h"
#include "a90_wifi.h"
#include "a90_wificfg.h"

#define A90_APP_WIFI_LINE_COUNT 8
#define A90_APP_WIFI_SCAN_DELAY_MS 5000

static bool app_wifi_scan_done;
static bool app_wifi_ping_done;
static struct a90_wifi_scan_snapshot app_wifi_scan_snapshot;
static struct a90_wifi_ping_snapshot app_wifi_ping_snapshot;

static uint32_t app_wifi_text_scale(void) {
    struct a90_kms_info info;

    a90_kms_info(&info);
    if (info.width >= 1080) {
        return 5;
    }
    if (info.width >= 720) {
        return 4;
    }
    return 3;
}

static uint32_t app_wifi_shrink_text_scale(const char *text,
                                           uint32_t scale,
                                           uint32_t max_width) {
    while (scale > 1 && (uint32_t)strlen(text) * scale * 6 > max_width) {
        --scale;
    }
    return scale;
}

static int app_wifi_draw_lines(const char *title,
                               const char *const *lines,
                               size_t line_count,
                               const char *footer,
                               uint32_t accent) {
    uint32_t scale;
    uint32_t title_scale;
    uint32_t x;
    uint32_t y;
    uint32_t card_w;
    uint32_t line_h;
    size_t index;

    if (a90_kms_begin_frame(0x050505) < 0) {
        return negative_errno_or(ENODEV);
    }

    scale = app_wifi_text_scale();
    title_scale = scale + 1;
    x = a90_kms_framebuffer()->width / 18;
    if (x < scale * 4) {
        x = scale * 4;
    }
    y = a90_kms_framebuffer()->height / 10;
    card_w = a90_kms_framebuffer()->width - (x * 2);
    line_h = scale * 11;

    a90_draw_text(a90_kms_framebuffer(), x, y, title, accent,
                  app_wifi_shrink_text_scale(title, title_scale, card_w));
    y += line_h + scale * 4;

    a90_draw_rect(a90_kms_framebuffer(),
                  x - scale,
                  y - scale,
                  card_w,
                  line_h * ((uint32_t)line_count + 1U),
                  0x202020);
    for (index = 0; index < line_count; ++index) {
        const char *line = lines[index] != NULL ? lines[index] : "";

        a90_draw_text(a90_kms_framebuffer(),
                      x,
                      y + (uint32_t)index * line_h,
                      line,
                      0xffffff,
                      app_wifi_shrink_text_scale(line, scale, card_w - scale * 2));
    }

    a90_draw_text(a90_kms_framebuffer(),
                  x,
                  a90_kms_framebuffer()->height - scale * 12,
                  footer,
                  0xffffff,
                  app_wifi_shrink_text_scale(footer, scale, card_w));

    if (a90_kms_present("screenwifi", true) < 0) {
        return negative_errno_or(EIO);
    }
    return 0;
}

static const char *app_wifi_text_or_dash(const char *text) {
    return text != NULL && text[0] != '\0' ? text : "-";
}

static const char *app_wifi_decision_badge(const char *decision) {
    if (decision == NULL || decision[0] == '\0' || strcmp(decision, "-") == 0) {
        return "INFO";
    }
    if (strstr(decision, "disabled") != NULL) {
        return "OFF";
    }
    if (strstr(decision, "running") != NULL || strstr(decision, "in-progress") != NULL) {
        return "RUN";
    }
    if (strstr(decision, "pass") != NULL ||
        strstr(decision, "carrier-up") != NULL ||
        strstr(decision, "wlan0-present") != NULL) {
        return "PASS";
    }
    if (strstr(decision, "failed") != NULL ||
        strstr(decision, "timeout") != NULL ||
        strstr(decision, "missing") != NULL ||
        strstr(decision, "blocked") != NULL) {
        return "FAIL";
    }
    if (strstr(decision, "no-config") != NULL) {
        return "NO_CFG";
    }
    return "INFO";
}

void a90_app_wifi_reset(enum screen_app_id app_id) {
    if (app_id == SCREEN_APP_WIFI_SCAN) {
        memset(&app_wifi_scan_snapshot, 0, sizeof(app_wifi_scan_snapshot));
        app_wifi_scan_done = false;
    } else if (app_id == SCREEN_APP_WIFI_PING) {
        memset(&app_wifi_ping_snapshot, 0, sizeof(app_wifi_ping_snapshot));
        app_wifi_ping_done = false;
    }
}

int a90_app_wifi_draw_status(void) {
    struct a90_wifi_status_snapshot status;
    char line0[256];
    char line1[256];
    char line2[256];
    char line3[256];
    char line4[256];
    char line5[256];
    char line6[256];
    char line7[256];
    const char *lines[A90_APP_WIFI_LINE_COUNT];
    const char *runtime_badge;
    const char *auto_badge;

    (void)a90_wifi_status_snapshot(&status);
    runtime_badge = app_wifi_decision_badge(status.runtime_decision);
    auto_badge = app_wifi_decision_badge(status.autoconnect_decision);
    snprintf(line0, sizeof(line0), "IF %s %s OPER %s CARRIER %s",
             status.iface,
             status.wlan0_present ? "PRESENT" : "MISSING",
             app_wifi_text_or_dash(status.operstate),
             app_wifi_text_or_dash(status.carrier));
    snprintf(line1, sizeof(line1), "IP %s  MAC %s",
             app_wifi_text_or_dash(status.ipv4),
             app_wifi_text_or_dash(status.mac));
    snprintf(line2, sizeof(line2), "CONN %s  WPA %s",
             app_wifi_text_or_dash(status.runtime_ssid_label),
             app_wifi_text_or_dash(status.runtime_wpa_state));
    snprintf(line3, sizeof(line3), "RF RSSI %s dBm  LINK %s Mbps  FREQ %s",
             app_wifi_text_or_dash(status.runtime_rssi),
             app_wifi_text_or_dash(status.runtime_linkspeed),
             app_wifi_text_or_dash(status.runtime_freq_mhz));
    snprintf(line4, sizeof(line4), "NET ROUTE %d NS %d GW %s",
             status.route_default_present ? 1 : 0,
             status.nameserver_count >= 0 ? status.nameserver_count : 0,
             app_wifi_text_or_dash(status.gateway));
    snprintf(line5, sizeof(line5), "AUTO %s PROFILE %s CARRIER %s",
             auto_badge,
             app_wifi_text_or_dash(status.autoconnect_profile),
             app_wifi_text_or_dash(status.autoconnect_carrier_up));
    snprintf(line6, sizeof(line6), "AUTO DECISION %s  NS %s",
             app_wifi_text_or_dash(status.autoconnect_decision),
             app_wifi_text_or_dash(status.autoconnect_nameserver_count));
    snprintf(line7, sizeof(line7), "RUN %s %s CTRL %s",
             runtime_badge,
             app_wifi_text_or_dash(status.runtime_decision),
             app_wifi_text_or_dash(status.ctrl_socket_kind));

    lines[0] = line0;
    lines[1] = line1;
    lines[2] = line2;
    lines[3] = line3;
    lines[4] = line4;
    lines[5] = line5;
    lines[6] = line6;
    lines[7] = line7;
    return app_wifi_draw_lines("WIFI STATUS", lines, A90_APP_WIFI_LINE_COUNT,
                               "PRESS ANY BUTTON TO RETURN", 0x66ccff);
}

int a90_app_wifi_draw_profiles(void) {
    struct a90_wificfg_profile_list list;
    char line0[256];
    char line1[256];
    char entry_lines[6][384];
    const char *lines[A90_APP_WIFI_LINE_COUNT];
    int index;

    (void)a90_wificfg_collect_profile_list(&list);
    snprintf(line0, sizeof(line0), "AUTO %s PROFILE %s",
             list.autoconnect.enabled ? "ENABLED" : "DISABLED",
             app_wifi_text_or_dash(list.autoconnect.profile));
    snprintf(line1, sizeof(line1), "COUNT %d STORED %d DUP %d OVF %d",
             list.profile_count,
             list.stored_count,
             list.duplicate_count,
             list.overflow_count);
    lines[0] = line0;
    lines[1] = line1;

    for (index = 0; index < 6; ++index) {
        if (index < list.stored_count) {
            const struct a90_wificfg_profile_summary *profile = &list.profiles[index];

            snprintf(entry_lines[index],
                     sizeof(entry_lines[index]),
                     "%d %s %s EN%d PR%d %s",
                     index + 1,
                     app_wifi_text_or_dash(profile->name),
                     app_wifi_text_or_dash(profile->band),
                     profile->enabled,
                     profile->priority,
                     app_wifi_text_or_dash(profile->decision));
        } else if (index == 0 && list.profile_count == 0) {
            snprintf(entry_lines[index], sizeof(entry_lines[index]), "%s", "NO WIFI PROFILES FOUND");
        } else {
            snprintf(entry_lines[index], sizeof(entry_lines[index]), "%s", "");
        }
        lines[index + 2] = entry_lines[index];
    }

    return app_wifi_draw_lines("WIFI PROFILES", lines, A90_APP_WIFI_LINE_COUNT,
                               "PRESS ANY BUTTON TO RETURN", 0x66ccff);
}

static int app_wifi_draw_scan_progress(void) {
    const char *lines[A90_APP_WIFI_LINE_COUNT] = {
        "SCANNING WLAN0 WITH NL80211",
        "ACTIVE RF SCAN: YES",
        "CONNECT: NO",
        "DHCP/ROUTE: NO",
        "EXTERNAL PING: NO",
        "CREDENTIALS: NOT READ",
        "RAW RESULTS: SCREEN ONLY",
        "WAITING...",
    };

    return app_wifi_draw_lines("WIFI SCAN", lines, A90_APP_WIFI_LINE_COUNT,
                               "SCAN RUNS ONCE, THEN RESULTS STAY ON SCREEN", 0xffcc33);
}

int a90_app_wifi_draw_scan(void) {
    char line0[256];
    char line1[256];
    char entry_lines[6][256];
    const char *lines[A90_APP_WIFI_LINE_COUNT];
    int index;

    if (!app_wifi_scan_done) {
        (void)app_wifi_draw_scan_progress();
        (void)a90_wifi_scan_collect(A90_APP_WIFI_SCAN_DELAY_MS, &app_wifi_scan_snapshot);
        app_wifi_scan_done = true;
    }

    snprintf(line0, sizeof(line0), "%s COUNT %d STORED %d RC %d",
             app_wifi_text_or_dash(app_wifi_scan_snapshot.decision),
             app_wifi_scan_snapshot.scan_result_count,
             app_wifi_scan_snapshot.stored_count,
             app_wifi_scan_snapshot.rc);
    snprintf(line1, sizeof(line1), "LINK %d FAM %d TRIG %d/%d DELAY %dms",
             app_wifi_scan_snapshot.link_up_rc,
             app_wifi_scan_snapshot.family_id,
             app_wifi_scan_snapshot.trigger_rc,
             app_wifi_scan_snapshot.trigger_errno,
             app_wifi_scan_snapshot.delay_ms);
    lines[0] = line0;
    lines[1] = line1;

    for (index = 0; index < 6; ++index) {
        if (index < app_wifi_scan_snapshot.stored_count) {
            const struct a90_wifi_scan_result *result =
                &app_wifi_scan_snapshot.results[index];

            snprintf(entry_lines[index],
                     sizeof(entry_lines[index]),
                     "%d %s  %dMHz  %s%d dBm  %s",
                     index + 1,
                     app_wifi_text_or_dash(result->ssid),
                     result->freq_mhz,
                     result->signal_valid ? "" : "?",
                     result->signal_dbm,
                     app_wifi_text_or_dash(result->security));
        } else if (index == 0 && app_wifi_scan_snapshot.scan_result_count == 0) {
            snprintf(entry_lines[index], sizeof(entry_lines[index]), "%s", "NO BSS ENTRIES");
        } else {
            snprintf(entry_lines[index], sizeof(entry_lines[index]), "%s", "");
        }
        lines[index + 2] = entry_lines[index];
    }

    return app_wifi_draw_lines("WIFI SCAN RESULTS", lines, A90_APP_WIFI_LINE_COUNT,
                               "PRESS ANY BUTTON TO RETURN", 0xffcc33);
}

static int app_wifi_draw_ping_progress(void) {
    const char *lines[A90_APP_WIFI_LINE_COUNT] = {
        "PINGING DHCP GATEWAY",
        "PINGING INTERNET TARGET 1.1.1.1",
        "COUNT: 3",
        "TIMEOUT: 2s EACH",
        "CONNECT: NO",
        "DHCP: NO",
        "CREDENTIALS: NOT READ",
        "WAITING...",
    };

    return app_wifi_draw_lines("WIFI PING TEST", lines, A90_APP_WIFI_LINE_COUNT,
                               "RUNS ONCE, THEN RESULTS STAY ON SCREEN", 0x99ff66);
}

static const char *app_wifi_ping_result_word(const struct a90_wifi_ping_target_result *result) {
    if (result == NULL || !result->requested) {
        return "SKIP";
    }
    if (!result->executed) {
        return "NOTRUN";
    }
    return result->success ? "PASS" : "FAIL";
}

static void app_wifi_ping_target_line(char *out,
                                      size_t out_size,
                                      const char *label,
                                      const struct a90_wifi_ping_target_result *result) {
    if (out == NULL || out_size == 0 || result == NULL) {
        return;
    }
    snprintf(out,
             out_size,
             "%s %s RX %d/%d LOSS %d%% AVG %sms",
             label,
             app_wifi_ping_result_word(result),
             result->packets_received,
             result->packets_transmitted,
             result->packet_loss_percent,
             app_wifi_text_or_dash(result->rtt_avg_ms));
}

int a90_app_wifi_draw_ping(void) {
    char line0[256];
    char line1[256];
    char line2[256];
    char line3[256];
    char line4[256];
    char line5[256];
    char line6[256];
    char line7[256];
    const char *lines[A90_APP_WIFI_LINE_COUNT];

    if (!app_wifi_ping_done) {
        (void)app_wifi_draw_ping_progress();
        (void)a90_wifi_ping_collect("all", &app_wifi_ping_snapshot);
        app_wifi_ping_done = true;
    }

    snprintf(line0,
             sizeof(line0),
             "%s RC %d COUNT %d TIMEOUT %ds",
             app_wifi_text_or_dash(app_wifi_ping_snapshot.decision),
             app_wifi_ping_snapshot.rc,
             app_wifi_ping_snapshot.count,
             app_wifi_ping_snapshot.timeout_sec);
    snprintf(line1,
             sizeof(line1),
             "WLAN0 %d CARRIER %d ROUTE %d BUSYBOX %d",
             app_wifi_ping_snapshot.wlan0_present ? 1 : 0,
             app_wifi_ping_snapshot.carrier_up ? 1 : 0,
             app_wifi_ping_snapshot.route_default_present ? 1 : 0,
             app_wifi_ping_snapshot.busybox_executable ? 1 : 0);
    app_wifi_ping_target_line(line2, sizeof(line2), "GATEWAY", &app_wifi_ping_snapshot.gateway);
    app_wifi_ping_target_line(line3, sizeof(line3), "INTERNET", &app_wifi_ping_snapshot.internet);
    snprintf(line4,
             sizeof(line4),
             "GW LOG %s",
             app_wifi_text_or_dash(app_wifi_ping_snapshot.gateway.log_path));
    snprintf(line5,
             sizeof(line5),
             "NET LOG %s",
             app_wifi_text_or_dash(app_wifi_ping_snapshot.internet.log_path));
    snprintf(line6, sizeof(line6), "GW TARGET REDACTED %d",
             app_wifi_ping_snapshot.gateway.target_redacted ? 1 : 0);
    snprintf(line7, sizeof(line7), "EXTERNAL PING: EXPLICIT USER ACTION");

    lines[0] = line0;
    lines[1] = line1;
    lines[2] = line2;
    lines[3] = line3;
    lines[4] = line4;
    lines[5] = line5;
    lines[6] = line6;
    lines[7] = line7;
    return app_wifi_draw_lines("WIFI PING RESULTS", lines, A90_APP_WIFI_LINE_COUNT,
                               "PRESS ANY BUTTON TO RETURN", 0x99ff66);
}
