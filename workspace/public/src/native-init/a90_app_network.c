#include "a90_app_network.h"

#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "a90_draw.h"
#include "a90_kms.h"
#include "a90_netservice.h"
#include "a90_util.h"

static uint32_t app_network_text_scale(void) {
    struct a90_kms_info info;

    a90_kms_info(&info);
    if (info.width >= 1080) {
        return 6;
    }
    if (info.width >= 720) {
        return 4;
    }
    return 3;
}

static uint32_t app_network_shrink_text_scale(const char *text,
                                              uint32_t scale,
                                              uint32_t max_width) {
    while (scale > 1 && (uint32_t)strlen(text) * scale * 6 > max_width) {
        --scale;
    }
    return scale;
}

static int app_network_draw_info_page(const char *title,
                                      const char *line1,
                                      const char *line2,
                                      const char *line3,
                                      const char *line4) {
    const char *footer = "PRESS ANY BUTTON TO RETURN";
    const char *lines[4];
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

    lines[0] = line1;
    lines[1] = line2;
    lines[2] = line3;
    lines[3] = line4;

    scale = app_network_text_scale();
    title_scale = scale + 1;
    x = a90_kms_framebuffer()->width / 18;
    if (x < scale * 4) {
        x = scale * 4;
    }
    y = a90_kms_framebuffer()->height / 8;
    card_w = a90_kms_framebuffer()->width - (x * 2);
    line_h = scale * 12;

    a90_draw_text(a90_kms_framebuffer(), x, y, title, 0xffcc33,
                  app_network_shrink_text_scale(title, title_scale, card_w));
    y += line_h + scale * 4;

    a90_draw_rect(a90_kms_framebuffer(), x - scale, y - scale, card_w, line_h * 5, 0x202020);
    for (index = 0; index < 4; ++index) {
        const char *line = lines[index] != NULL ? lines[index] : "";

        a90_draw_text(a90_kms_framebuffer(), x, y + (uint32_t)index * line_h,
                      line,
                      0xffffff,
                      app_network_shrink_text_scale(line, scale, card_w - scale * 2));
    }

    a90_draw_text(a90_kms_framebuffer(), x, a90_kms_framebuffer()->height - scale * 12,
                  footer, 0xffffff,
                  app_network_shrink_text_scale(footer, scale, card_w));

    if (a90_kms_present("screeninfo", true) < 0) {
        return negative_errno_or(EIO);
    }
    return 0;
}

int a90_app_network_draw_summary(void) {
    char line1[96];
    char line2[96];
    char line3[96];
    char line4[96];
    struct a90_netservice_status status;

    a90_netservice_status(&status);
    snprintf(line1, sizeof(line1), "NETSERVICE %s",
             status.enabled ? "ENABLED" : "DISABLED");
    snprintf(line2, sizeof(line2), "%s %s %s",
             status.ifname,
             status.ncm_present ? "PRESENT" : "ABSENT",
             status.device_ip);
    if (status.tcpctl_running) {
        snprintf(line3, sizeof(line3), "TCPCTL RUNNING PID %ld",
                 (long)status.tcpctl_pid);
    } else {
        snprintf(line3, sizeof(line3), "TCPCTL STOPPED");
    }
    snprintf(line4, sizeof(line4), "PORT %s LOG %s", status.tcp_port, status.log_path);

    return app_network_draw_info_page("NETWORK STATUS", line1, line2, line3, line4);
}
