/* Included by stage3/linux_init/init_v86.c. Do not compile standalone. */

static int read_long_value(const char *path, long *value_out) {
    char buf[128];

    if (read_trimmed_text_file(path, buf, sizeof(buf)) < 0) {
        return -1;
    }

    *value_out = strtol(buf, NULL, 10);
    return 0;
}

static int read_first_token(const char *path, char *out, size_t out_size) {
    char buf[256];
    size_t len = 0;

    if (read_trimmed_text_file(path, buf, sizeof(buf)) < 0) {
        return -1;
    }

    while (buf[len] != '\0' && buf[len] != ' ' && buf[len] != '\t' && len + 1 < out_size) {
        out[len] = buf[len];
        ++len;
    }
    out[len] = '\0';
    return 0;
}

static int read_meminfo_kb(const char *label, long *value_out) {
    FILE *fp;
    char line[256];
    size_t label_len = strlen(label);

    fp = fopen("/proc/meminfo", "r");
    if (fp == NULL) {
        return -1;
    }

    while (fgets(line, sizeof(line), fp) != NULL) {
        if (strncmp(line, label, label_len) == 0) {
            char *cursor = line + label_len;
            while (*cursor == ' ' || *cursor == '\t' || *cursor == ':') {
                ++cursor;
            }
            *value_out = strtol(cursor, NULL, 10);
            fclose(fp);
            return 0;
        }
    }

    fclose(fp);
    errno = ENOENT;
    return -1;
}

static int read_cpu_usage_percent(long *percent_out) {
    static bool have_previous = false;
    static unsigned long long previous_total = 0;
    static unsigned long long previous_idle = 0;
    FILE *fp;
    char line[256];
    unsigned long long user = 0;
    unsigned long long nice = 0;
    unsigned long long system = 0;
    unsigned long long idle = 0;
    unsigned long long iowait = 0;
    unsigned long long irq = 0;
    unsigned long long softirq = 0;
    unsigned long long steal = 0;
    unsigned long long idle_all;
    unsigned long long non_idle;
    unsigned long long total;
    unsigned long long total_delta;
    unsigned long long idle_delta;
    unsigned long long busy_delta;
    long percent;

    fp = fopen("/proc/stat", "r");
    if (fp == NULL) {
        return -1;
    }

    if (fgets(line, sizeof(line), fp) == NULL) {
        fclose(fp);
        return -1;
    }
    fclose(fp);

    if (sscanf(line, "cpu %llu %llu %llu %llu %llu %llu %llu %llu",
               &user,
               &nice,
               &system,
               &idle,
               &iowait,
               &irq,
               &softirq,
               &steal) < 4) {
        return -1;
    }

    idle_all = idle + iowait;
    non_idle = user + nice + system + irq + softirq + steal;
    total = idle_all + non_idle;

    if (!have_previous || total <= previous_total) {
        previous_total = total;
        previous_idle = idle_all;
        have_previous = true;
        return -1;
    }

    total_delta = total - previous_total;
    idle_delta = idle_all - previous_idle;
    previous_total = total;
    previous_idle = idle_all;

    if (total_delta == 0 || idle_delta > total_delta) {
        return -1;
    }

    busy_delta = total_delta - idle_delta;
    percent = (long)((busy_delta * 100ULL + total_delta / 2ULL) / total_delta);
    if (percent < 0) {
        percent = 0;
    } else if (percent > 100) {
        percent = 100;
    }

    *percent_out = percent;
    return 0;
}

static int read_gpu_busy_percent(long *percent_out) {
    char buf[64];
    long percent;

    if (read_trimmed_text_file("/sys/class/kgsl/kgsl-3d0/gpu_busy_percentage",
                               buf,
                               sizeof(buf)) < 0) {
        return -1;
    }

    percent = strtol(buf, NULL, 10);
    if (percent < 0) {
        percent = 0;
    } else if (percent > 100) {
        percent = 100;
    }

    *percent_out = percent;
    return 0;
}

static int read_average_thermal_temp(const char *prefix_a,
                                     const char *prefix_b,
                                     long *temp_out) {
    DIR *dir;
    struct dirent *entry;
    long total = 0;
    long count = 0;

    dir = opendir("/sys/class/thermal");
    if (dir == NULL) {
        return -1;
    }

    while ((entry = readdir(dir)) != NULL) {
        char type_path[PATH_MAX];
        char temp_path[PATH_MAX];
        char type[128];
        long temp_value;

        if (strncmp(entry->d_name, "thermal_zone", 12) != 0) {
            continue;
        }

        if (snprintf(type_path, sizeof(type_path),
                     "/sys/class/thermal/%s/type", entry->d_name) >= (int)sizeof(type_path) ||
            snprintf(temp_path, sizeof(temp_path),
                     "/sys/class/thermal/%s/temp", entry->d_name) >= (int)sizeof(temp_path)) {
            continue;
        }

        if (read_trimmed_text_file(type_path, type, sizeof(type)) < 0 ||
            read_long_value(temp_path, &temp_value) < 0) {
            continue;
        }

        if (strncmp(type, prefix_a, strlen(prefix_a)) == 0 ||
            (prefix_b != NULL && strncmp(type, prefix_b, strlen(prefix_b)) == 0)) {
            total += temp_value;
            ++count;
        }
    }

    closedir(dir);

    if (count == 0) {
        errno = ENOENT;
        return -1;
    }

    *temp_out = total / count;
    return 0;
}

static void format_temp_tenths(char *out, size_t out_size, long milli_c) {
    long tenths = milli_c / 100;
    long whole = tenths / 10;
    long frac = tenths % 10;

    if (frac < 0) {
        frac = -frac;
    }

    snprintf(out, out_size, "%ld.%ldC", whole, frac);
}

struct status_snapshot {
    char battery_status[64];
    char battery_pct[32];
    char battery_temp[32];
    char battery_voltage[32];
    char cpu_temp[32];
    char cpu_usage[16];
    char gpu_temp[32];
    char gpu_usage[16];
    char memory[64];
    char loadavg[32];
    char uptime[32];
    char power_now[32];
    char power_avg[32];
};

static void format_milliwatts_as_watts(char *out, size_t out_size, long milliwatts) {
    long tenths = milliwatts / 100;
    long whole = tenths / 10;
    long frac = tenths % 10;

    if (frac < 0) {
        frac = -frac;
    }

    snprintf(out, out_size, "%ld.%ldW", whole, frac);
}

static void read_status_snapshot(struct status_snapshot *snapshot) {
    long value;
    long mem_total_kb;
    long mem_avail_kb;

    strcpy(snapshot->battery_status, "?");
    strcpy(snapshot->battery_pct, "?");
    strcpy(snapshot->battery_temp, "?");
    strcpy(snapshot->battery_voltage, "?");
    strcpy(snapshot->cpu_temp, "?");
    strcpy(snapshot->cpu_usage, "?");
    strcpy(snapshot->gpu_temp, "?");
    strcpy(snapshot->gpu_usage, "?");
    strcpy(snapshot->memory, "?");
    strcpy(snapshot->loadavg, "?");
    strcpy(snapshot->uptime, "?");
    strcpy(snapshot->power_now, "?");
    strcpy(snapshot->power_avg, "?");

    if (read_long_value("/sys/class/power_supply/battery/capacity", &value) == 0) {
        snprintf(snapshot->battery_pct, sizeof(snapshot->battery_pct), "%ld%%", value);
    }
    if (read_trimmed_text_file("/sys/class/power_supply/battery/status",
                               snapshot->battery_status,
                               sizeof(snapshot->battery_status)) < 0) {
        strcpy(snapshot->battery_status, "?");
    }
    if (read_long_value("/sys/class/power_supply/battery/temp", &value) == 0) {
        format_temp_tenths(snapshot->battery_temp, sizeof(snapshot->battery_temp), value * 100);
    }
    if (read_long_value("/sys/class/power_supply/battery/voltage_now", &value) == 0) {
        snprintf(snapshot->battery_voltage, sizeof(snapshot->battery_voltage), "%ldmV", value / 1000);
    }
    if (read_long_value("/sys/class/power_supply/battery/power_now", &value) == 0) {
        format_milliwatts_as_watts(snapshot->power_now, sizeof(snapshot->power_now), value);
    }
    if (read_long_value("/sys/class/power_supply/battery/power_avg", &value) == 0) {
        format_milliwatts_as_watts(snapshot->power_avg, sizeof(snapshot->power_avg), value);
    }
    if (read_average_thermal_temp("cpu-", "cpuss", &value) == 0) {
        format_temp_tenths(snapshot->cpu_temp, sizeof(snapshot->cpu_temp), value);
    }
    if (read_cpu_usage_percent(&value) == 0) {
        snprintf(snapshot->cpu_usage, sizeof(snapshot->cpu_usage), "%ld%%", value);
    }
    if (read_average_thermal_temp("gpuss", NULL, &value) == 0) {
        format_temp_tenths(snapshot->gpu_temp, sizeof(snapshot->gpu_temp), value);
    }
    if (read_gpu_busy_percent(&value) == 0) {
        snprintf(snapshot->gpu_usage, sizeof(snapshot->gpu_usage), "%ld%%", value);
    }
    if (read_meminfo_kb("MemTotal", &mem_total_kb) == 0 &&
        read_meminfo_kb("MemAvailable", &mem_avail_kb) == 0) {
        snprintf(snapshot->memory, sizeof(snapshot->memory), "%ld/%ldMB",
                 (mem_total_kb - mem_avail_kb) / 1024,
                 mem_total_kb / 1024);
    }
    read_first_token("/proc/loadavg", snapshot->loadavg, sizeof(snapshot->loadavg));
    read_first_token("/proc/uptime", snapshot->uptime, sizeof(snapshot->uptime));
}

static void kms_draw_status_overlay(struct a90_fb *fb,
                                    unsigned int refresh_sec,
                                    unsigned int sequence) {
    struct status_snapshot snapshot;
    char boot_summary[64];
    char bat_tag[8];
    char footer[32];
    char storage_line[96];
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
    uint32_t off;
    long bat_pct_val;

    (void)refresh_sec;
    (void)sequence;

    if (y > glyph_h + glyph_h / 2 + scale * 2)
        y -= glyph_h + glyph_h / 2;

    read_status_snapshot(&snapshot);
    a90_timeline_boot_summary(boot_summary, sizeof(boot_summary));

    bat_tag[0] = '\0';
    if (strncmp(snapshot.battery_status, "Charging", 8) == 0)
        strncpy(bat_tag, "CHG", sizeof(bat_tag) - 1);
    else if (strncmp(snapshot.battery_status, "Full", 4) == 0)
        strncpy(bat_tag, "FUL", sizeof(bat_tag) - 1);
    else if (strncmp(snapshot.battery_status, "Discharging", 11) == 0)
        strncpy(bat_tag, "DSC", sizeof(bat_tag) - 1);

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

    /* 4 card backgrounds */
    a90_draw_rect(fb, x - scale, y + slot * 0 - scale, card_w, card_h, 0x202020);
    a90_draw_rect(fb, x - scale, y + slot * 1 - scale, card_w, card_h, 0x202020);
    a90_draw_rect(fb, x - scale, y + slot * 2 - scale, card_w, card_h, 0x202020);
    a90_draw_rect(fb, x - scale, y + slot * 3 - scale, card_w, card_h, 0x202020);

    /* Row 0: "A90 INIT "(gray) + boot_summary(colored) */
    a90_draw_text(fb, x, y + slot * 0, "A90 INIT ", 0x909090, scale);
    a90_draw_text(fb, x + 9 * char_w, y + slot * 0, boot_summary, boot_color, scale);

    /* Row 1: "BAT "(gray) pct(colored) tag(colored) " PWR "(gray) now(white) " AVG "(gray) avg(white) */
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

    /* Row 2: "CPU "(gray) cpu_temp/usage(white) " GPU "(gray) gpu_temp/usage(white) */
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

    /* Row 3: "MEM "(gray) memory(white) " LOAD "(gray) loadavg(white) */
    off = 0;
    a90_draw_text(fb, x + off * char_w, y + slot * 3, "MEM ", 0x909090, scale); off += 4;
    a90_draw_text(fb, x + off * char_w, y + slot * 3, snapshot.memory, 0xffffff, scale);
    off += (uint32_t)strlen(snapshot.memory) + 1;
    a90_draw_text(fb, x + off * char_w, y + slot * 3, "LOAD ", 0x909090, scale); off += 5;
    a90_draw_text(fb, x + off * char_w, y + slot * 3, snapshot.loadavg, 0xffffff, scale);

    if (boot_storage.warning[0] != '\0') {
        snprintf(storage_line, sizeof(storage_line), "SD WARN %.70s", boot_storage.warning);
        storage_color = 0xffcc33;
    } else {
        snprintf(storage_line, sizeof(storage_line), "STORAGE %s %.60s",
                 boot_storage.backend,
                 boot_storage.root);
        storage_color = 0x88ee88;
    }
    storage_line[sizeof(storage_line) - 1] = '\0';
    a90_draw_text(fb, x, y + slot * 4, storage_line, storage_color, scale > 3 ? scale - 2 : scale);

    a90_draw_text(fb, x, footer_text_y, footer, 0xbbbbbb, footer_scale);
}

static bool parse_color_arg(const char *arg, uint32_t *color_out) {
    unsigned int value;

    if (strcmp(arg, "black") == 0) {
        *color_out = 0x000000;
        return true;
    }
    if (strcmp(arg, "white") == 0) {
        *color_out = 0xffffff;
        return true;
    }
    if (strcmp(arg, "red") == 0) {
        *color_out = 0xff0000;
        return true;
    }
    if (strcmp(arg, "green") == 0) {
        *color_out = 0x00ff00;
        return true;
    }
    if (strcmp(arg, "blue") == 0) {
        *color_out = 0x0000ff;
        return true;
    }
    if (strcmp(arg, "gray") == 0 || strcmp(arg, "grey") == 0) {
        *color_out = 0x808080;
        return true;
    }
    if (sscanf(arg, "%x", &value) == 1) {
        *color_out = value & 0xffffffU;
        return true;
    }
    return false;
}

static int cmd_kmsprobe(void) {
    return a90_kms_probe(true);
}

static int cmd_kmssolid(char **argv, int argc) {
    uint32_t color = 0x000000;

    if (argc >= 2 && !parse_color_arg(argv[1], &color)) {
        a90_console_printf("usage: kmssolid [black|white|red|green|blue|gray|0xRRGGBB]\r\n");
        return -EINVAL;
    }

    if (a90_kms_begin_frame(color) < 0) {
        return negative_errno_or(ENODEV);
    }
    if (a90_kms_present("kmssolid", true) < 0) {
        return negative_errno_or(EIO);
    }
    return 0;
}

static int cmd_kmsframe(void) {
    if (a90_kms_begin_frame(0x080808) < 0) {
        return negative_errno_or(ENODEV);
    }
    a90_draw_boot_frame(a90_kms_framebuffer());
    if (a90_kms_present("kmsframe", true) < 0) {
        return negative_errno_or(EIO);
    }
    return 0;
}

static int cmd_statusscreen(void) {
    if (a90_kms_begin_frame(0x000000) < 0) {
        return negative_errno_or(ENODEV);
    }
    a90_console_printf("statusscreen: drawing giant TEST probe\r\n");
    a90_draw_giant_test_probe(a90_kms_framebuffer());
    if (a90_kms_present("statusscreen", true) < 0) {
        return negative_errno_or(EIO);
    }
    return 0;
}

static int cmd_statushud(void) {
    if (a90_kms_begin_frame(0x000000) < 0) {
        return negative_errno_or(ENODEV);
    }
    a90_console_printf("statushud: drawing sensor HUD\r\n");
    kms_draw_status_overlay(a90_kms_framebuffer(), 0, 1);
    if (a90_kms_present("statushud", true) < 0) {
        return negative_errno_or(EIO);
    }
    return 0;
}

static int wait_watch_delay(int refresh_sec) {
    int remaining_ticks = refresh_sec * 10;

    while (remaining_ticks-- > 0) {
        enum a90_cancel_kind cancel = a90_console_poll_cancel(100);

        if (cancel != CANCEL_NONE) {
            return a90_console_cancelled("watchhud", cancel);
        }
    }

    return 0;
}

static int clamp_hud_refresh(int refresh_sec);

static int cmd_watchhud(char **argv, int argc) {
    int refresh_sec = 2;
    int count = 0;
    int index = 0;
    int first_error = 0;
    bool drew_frame = false;

    if (argc >= 2 && sscanf(argv[1], "%d", &refresh_sec) != 1) {
        a90_console_printf("usage: watchhud [sec] [count]\r\n");
        return -EINVAL;
    }
    if (argc >= 3 && sscanf(argv[2], "%d", &count) != 1) {
        a90_console_printf("usage: watchhud [sec] [count]\r\n");
        return -EINVAL;
    }
    refresh_sec = clamp_hud_refresh(refresh_sec);

    a90_console_printf("watchhud: refresh=%ds count=%s, q/Ctrl-C cancels\r\n",
            refresh_sec,
            count > 0 ? argv[2] : "forever");

    while (count <= 0 || index < count) {
        if (a90_kms_begin_frame(0x000000) == 0) {
            kms_draw_status_overlay(a90_kms_framebuffer(), (unsigned int)refresh_sec, (unsigned int)(index + 1));
            if (a90_kms_present("watchhud", true) == 0) {
                drew_frame = true;
            } else if (first_error == 0) {
                first_error = negative_errno_or(EIO);
            }
        } else if (first_error == 0) {
            first_error = negative_errno_or(ENODEV);
        }
        ++index;
        if (count > 0 && index >= count) {
            break;
        }
        {
            int wait_rc = wait_watch_delay(refresh_sec);

            if (wait_rc < 0) {
                return wait_rc;
            }
        }
    }

    return drew_frame ? 0 : first_error;
}

static int clamp_hud_refresh(int refresh_sec) {
    if (refresh_sec < 1) {
        return 1;
    }
    if (refresh_sec > 60) {
        return 60;
    }
    return refresh_sec;
}

static void reap_hud_child(void) {
    if (a90_service_reap(A90_SERVICE_HUD, NULL) > 0) {
        clear_auto_menu_ipc();
    }
}

static void stop_auto_hud(bool verbose) {
    reap_hud_child();
    if (a90_service_pid(A90_SERVICE_HUD) <= 0) {
        if (verbose) {
            a90_console_printf("autohud: not running\r\n");
        }
        return;
    }

    (void)a90_service_stop(A90_SERVICE_HUD, 2000);
    clear_auto_menu_ipc();
    if (verbose) {
        a90_console_printf("autohud: stopped\r\n");
    }
}

/* forward declarations for auto_hud_loop */
