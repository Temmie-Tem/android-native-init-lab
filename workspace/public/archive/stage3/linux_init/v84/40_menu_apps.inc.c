/* Included by stage3/linux_init/init_v84.c. Do not compile standalone. */

enum screen_menu_page_id {
    SCREEN_MENU_PAGE_MAIN = 0,
    SCREEN_MENU_PAGE_APPS,
    SCREEN_MENU_PAGE_ABOUT,
    SCREEN_MENU_PAGE_CHANGELOG,
    SCREEN_MENU_PAGE_MONITORING,
    SCREEN_MENU_PAGE_TOOLS,
    SCREEN_MENU_PAGE_CPU_STRESS,
    SCREEN_MENU_PAGE_LOGS,
    SCREEN_MENU_PAGE_NETWORK,
    SCREEN_MENU_PAGE_POWER,
    SCREEN_MENU_PAGE_COUNT,
};

enum screen_menu_action {
    SCREEN_MENU_RESUME = 0,
    SCREEN_MENU_STATUS,
    SCREEN_MENU_LOG,
    SCREEN_MENU_NET_STATUS,
    SCREEN_MENU_ABOUT_VERSION,
    SCREEN_MENU_ABOUT_CHANGELOG,
    SCREEN_MENU_ABOUT_CREDITS,
    SCREEN_MENU_CHANGELOG_0815,
    SCREEN_MENU_CHANGELOG_0814,
    SCREEN_MENU_CHANGELOG_0813,
    SCREEN_MENU_CHANGELOG_0812,
    SCREEN_MENU_CHANGELOG_0811,
    SCREEN_MENU_CHANGELOG_0810,
    SCREEN_MENU_CHANGELOG_089,
    SCREEN_MENU_CHANGELOG_088,
    SCREEN_MENU_CHANGELOG_087,
    SCREEN_MENU_CHANGELOG_086,
    SCREEN_MENU_CHANGELOG_085,
    SCREEN_MENU_CHANGELOG_084,
    SCREEN_MENU_CHANGELOG_083,
    SCREEN_MENU_CHANGELOG_082,
    SCREEN_MENU_CHANGELOG_081,
    SCREEN_MENU_CHANGELOG_080,
    SCREEN_MENU_CHANGELOG_075,
    SCREEN_MENU_CHANGELOG_074,
    SCREEN_MENU_CHANGELOG_073,
    SCREEN_MENU_CHANGELOG_072,
    SCREEN_MENU_CHANGELOG_071,
    SCREEN_MENU_CHANGELOG_070,
    SCREEN_MENU_CHANGELOG_060,
    SCREEN_MENU_CHANGELOG_051,
    SCREEN_MENU_CHANGELOG_050,
    SCREEN_MENU_CHANGELOG_041,
    SCREEN_MENU_CHANGELOG_040,
    SCREEN_MENU_CHANGELOG_030,
    SCREEN_MENU_CHANGELOG_020,
    SCREEN_MENU_CHANGELOG_010,
    SCREEN_MENU_INPUT_MONITOR,
    SCREEN_MENU_DISPLAY_TEST,
    SCREEN_MENU_CUTOUT_CAL,
    SCREEN_MENU_CPU_STRESS_5,
    SCREEN_MENU_CPU_STRESS_10,
    SCREEN_MENU_CPU_STRESS_30,
    SCREEN_MENU_CPU_STRESS_60,
    SCREEN_MENU_BACK,
    SCREEN_MENU_SUBMENU,
    SCREEN_MENU_RECOVERY,
    SCREEN_MENU_REBOOT,
    SCREEN_MENU_POWEROFF,
};

enum screen_app_id {
    SCREEN_APP_NONE = 0,
    SCREEN_APP_LOG,
    SCREEN_APP_NETWORK,
    SCREEN_APP_ABOUT_VERSION,
    SCREEN_APP_ABOUT_CHANGELOG,
    SCREEN_APP_ABOUT_CREDITS,
    SCREEN_APP_CHANGELOG_0815,
    SCREEN_APP_CHANGELOG_0814,
    SCREEN_APP_CHANGELOG_0813,
    SCREEN_APP_CHANGELOG_0812,
    SCREEN_APP_CHANGELOG_0811,
    SCREEN_APP_CHANGELOG_0810,
    SCREEN_APP_CHANGELOG_089,
    SCREEN_APP_CHANGELOG_088,
    SCREEN_APP_CHANGELOG_087,
    SCREEN_APP_CHANGELOG_086,
    SCREEN_APP_CHANGELOG_085,
    SCREEN_APP_CHANGELOG_084,
    SCREEN_APP_CHANGELOG_083,
    SCREEN_APP_CHANGELOG_082,
    SCREEN_APP_CHANGELOG_081,
    SCREEN_APP_CHANGELOG_080,
    SCREEN_APP_CHANGELOG_075,
    SCREEN_APP_CHANGELOG_074,
    SCREEN_APP_CHANGELOG_073,
    SCREEN_APP_CHANGELOG_072,
    SCREEN_APP_CHANGELOG_071,
    SCREEN_APP_CHANGELOG_070,
    SCREEN_APP_CHANGELOG_060,
    SCREEN_APP_CHANGELOG_051,
    SCREEN_APP_CHANGELOG_050,
    SCREEN_APP_CHANGELOG_041,
    SCREEN_APP_CHANGELOG_040,
    SCREEN_APP_CHANGELOG_030,
    SCREEN_APP_CHANGELOG_020,
    SCREEN_APP_CHANGELOG_010,
    SCREEN_APP_INPUT_MONITOR,
    SCREEN_APP_DISPLAY_TEST,
    SCREEN_APP_CUTOUT_CAL,
    SCREEN_APP_CPU_STRESS,
};

enum cutout_calibration_field {
    CUTOUT_CAL_FIELD_X = 0,
    CUTOUT_CAL_FIELD_Y,
    CUTOUT_CAL_FIELD_SIZE,
    CUTOUT_CAL_FIELD_COUNT,
};

struct cutout_calibration_state {
    int center_x;
    int center_y;
    int size;
    enum cutout_calibration_field field;
};

struct screen_menu_item {
    const char *name;
    const char *summary;
    enum screen_menu_action action;
    enum screen_menu_page_id target;
};

struct screen_menu_page {
    const char *title;
    const struct screen_menu_item *items;
    size_t count;
    enum screen_menu_page_id parent;
};

struct key_wait_context { int fd0; int fd3; };
static int open_key_wait_context(struct key_wait_context *ctx, const char *tag);
static void close_key_wait_context(struct key_wait_context *ctx);
static void kms_draw_menu_section(struct kms_display_state *state,
                                  const struct screen_menu_page *page,
                                  size_t selected);
static void kms_draw_log_tail_panel(struct kms_display_state *state,
                                    uint32_t x,
                                    uint32_t y,
                                    uint32_t width,
                                    uint32_t bottom,
                                    int max_lines,
                                    const char *title,
                                    uint32_t scale);
static void kms_draw_hud_log_tail(struct kms_display_state *state);
static int cmd_statushud(void);
static int cmd_recovery(void);
static int draw_screen_log_summary(void);
static int draw_screen_network_summary(void);
static int draw_screen_about_version(void);
static int draw_screen_about_changelog(void);
static int draw_screen_about_credits(void);
static int draw_screen_changelog_detail(enum screen_app_id app_id);
static int draw_screen_input_monitor_app(void);
static int draw_screen_display_test_page(unsigned int page_index);
static int draw_screen_display_test(void);
static void cutout_calibration_init(struct cutout_calibration_state *cal);
static bool cutout_calibration_feed_key(struct cutout_calibration_state *cal,
                                        const struct input_event *event,
                                        unsigned int *down_mask,
                                        long *power_down_ms,
                                        long *last_power_up_ms);
static int draw_screen_cutout_calibration(const struct cutout_calibration_state *cal,
                                          bool interactive);
static int draw_screen_cpu_hint(void);
static int draw_screen_cpu_stress_app(bool running,
                                      bool done,
                                      bool failed,
                                      long remaining_ms,
                                      long duration_ms);
static uint32_t shrink_text_scale(const char *text, uint32_t scale, uint32_t max_width);
static void cpustress_worker(long deadline_ms, unsigned int worker_index);
static void cpustress_stop_workers(pid_t *pids, unsigned int workers);
static void restore_auto_hud_if_needed(bool restore_hud);
static void input_monitor_app_reset(void);
static void input_monitor_app_tick(void);
static bool input_monitor_app_feed_event(const struct input_event *event,
                                         int source_index);

#define SCREEN_MENU_COUNT(items) (sizeof(items) / sizeof((items)[0]))

static const struct screen_menu_item screen_menu_main_items[] = {
    { "APPS >",    "OPEN APP FOLDERS", SCREEN_MENU_SUBMENU, SCREEN_MENU_PAGE_APPS },
    { "STATUS",    "LIVE SYSTEM VIEW", SCREEN_MENU_STATUS, SCREEN_MENU_PAGE_MAIN },
    { "NETWORK >", "NCM AND TCPCTL",   SCREEN_MENU_SUBMENU, SCREEN_MENU_PAGE_NETWORK },
    { "POWER >",   "REBOOT OPTIONS",   SCREEN_MENU_SUBMENU, SCREEN_MENU_PAGE_POWER },
    { "HIDE MENU", "RETURN TO HUD",    SCREEN_MENU_RESUME, SCREEN_MENU_PAGE_MAIN },
};

static const struct screen_menu_item screen_menu_apps_items[] = {
    { "ABOUT >",      "VERSION AND CREDITS", SCREEN_MENU_SUBMENU, SCREEN_MENU_PAGE_ABOUT },
    { "MONITORING >", "STATUS APPLETS", SCREEN_MENU_SUBMENU, SCREEN_MENU_PAGE_MONITORING },
    { "TOOLS >",      "TEST HELPERS",   SCREEN_MENU_SUBMENU, SCREEN_MENU_PAGE_TOOLS },
    { "LOGS >",       "LOG VIEWERS",    SCREEN_MENU_SUBMENU, SCREEN_MENU_PAGE_LOGS },
    { "BACK",         "MAIN MENU",      SCREEN_MENU_BACK,    SCREEN_MENU_PAGE_MAIN },
};

static const struct screen_menu_item screen_menu_about_items[] = {
    { "VERSION",     "CURRENT BUILD",   SCREEN_MENU_ABOUT_VERSION,  SCREEN_MENU_PAGE_ABOUT },
    { "CHANGELOG >", "VERSION DETAILS", SCREEN_MENU_SUBMENU,        SCREEN_MENU_PAGE_CHANGELOG },
    { "CREDITS",     "MADE BY",         SCREEN_MENU_ABOUT_CREDITS,  SCREEN_MENU_PAGE_ABOUT },
    { "BACK",        "APPS",            SCREEN_MENU_BACK,           SCREEN_MENU_PAGE_APPS },
};

static const struct screen_menu_item screen_menu_changelog_items[] = {
    { "0.8.15 v84", "CMDPROTO API",       SCREEN_MENU_CHANGELOG_0815, SCREEN_MENU_PAGE_CHANGELOG },
    { "0.8.14 v83", "CONSOLE API",        SCREEN_MENU_CHANGELOG_0814, SCREEN_MENU_PAGE_CHANGELOG },
    { "0.8.13 v82", "LOG TIMELINE API",   SCREEN_MENU_CHANGELOG_0813, SCREEN_MENU_PAGE_CHANGELOG },
    { "0.8.12 v81", "CONFIG UTIL API",    SCREEN_MENU_CHANGELOG_0812, SCREEN_MENU_PAGE_CHANGELOG },
    { "0.8.11 v80", "SOURCE MODULES",     SCREEN_MENU_CHANGELOG_0811, SCREEN_MENU_PAGE_CHANGELOG },
    { "0.8.10 v79", "BOOT SD PROBE",      SCREEN_MENU_CHANGELOG_0810, SCREEN_MENU_PAGE_CHANGELOG },
    { "0.8.9 v78", "SD WORKSPACE",         SCREEN_MENU_CHANGELOG_089, SCREEN_MENU_PAGE_CHANGELOG },
    { "0.8.8 v77", "DISPLAY TEST PAGES",   SCREEN_MENU_CHANGELOG_088, SCREEN_MENU_PAGE_CHANGELOG },
    { "0.8.7 v76", "AT FRAGMENT FILTER",    SCREEN_MENU_CHANGELOG_087, SCREEN_MENU_PAGE_CHANGELOG },
    { "0.8.6 v75", "QUIET IDLE REATTACH",  SCREEN_MENU_CHANGELOG_086, SCREEN_MENU_PAGE_CHANGELOG },
    { "0.8.5 v74", "CMDV1 ARG ENCODING",   SCREEN_MENU_CHANGELOG_085, SCREEN_MENU_PAGE_CHANGELOG },
    { "0.8.4 v73", "CMDV1 PROTOCOL",       SCREEN_MENU_CHANGELOG_084, SCREEN_MENU_PAGE_CHANGELOG },
    { "0.8.3 v72", "DISPLAY TEST FIX",     SCREEN_MENU_CHANGELOG_083, SCREEN_MENU_PAGE_CHANGELOG },
    { "0.8.2 v71", "MENU LOG TAIL",        SCREEN_MENU_CHANGELOG_082, SCREEN_MENU_PAGE_CHANGELOG },
    { "0.8.1 v70", "INPUT MONITOR APP",    SCREEN_MENU_CHANGELOG_081, SCREEN_MENU_PAGE_CHANGELOG },
    { "0.8.0 v69", "INPUT GESTURE LAYOUT", SCREEN_MENU_CHANGELOG_080, SCREEN_MENU_PAGE_CHANGELOG },
    { "0.7.5 v68", "LOG TAIL + HISTORY",  SCREEN_MENU_CHANGELOG_075, SCREEN_MENU_PAGE_CHANGELOG },
    { "0.7.4 v67", "DETAIL CHANGELOG UI", SCREEN_MENU_CHANGELOG_074, SCREEN_MENU_PAGE_CHANGELOG },
    { "0.7.3 v66", "ABOUT + VERSIONING",  SCREEN_MENU_CHANGELOG_073, SCREEN_MENU_PAGE_CHANGELOG },
    { "0.7.2 v65", "SPLASH SAFE LAYOUT",  SCREEN_MENU_CHANGELOG_072, SCREEN_MENU_PAGE_CHANGELOG },
    { "0.7.1 v64", "CUSTOM BOOT SPLASH",  SCREEN_MENU_CHANGELOG_071, SCREEN_MENU_PAGE_CHANGELOG },
    { "0.7.0 v63", "APP MENU",            SCREEN_MENU_CHANGELOG_070, SCREEN_MENU_PAGE_CHANGELOG },
    { "0.6.0 v62", "CPU DIAGNOSTICS",     SCREEN_MENU_CHANGELOG_060, SCREEN_MENU_PAGE_CHANGELOG },
    { "0.5.1 v61", "CPU/GPU USAGE HUD",  SCREEN_MENU_CHANGELOG_051, SCREEN_MENU_PAGE_CHANGELOG },
    { "0.5.0 v60", "NETSERVICE BOOT",    SCREEN_MENU_CHANGELOG_050, SCREEN_MENU_PAGE_CHANGELOG },
    { "0.4.1 v59", "AT SERIAL FILTER",   SCREEN_MENU_CHANGELOG_041, SCREEN_MENU_PAGE_CHANGELOG },
    { "0.4.0 v55", "NCM TCP CONTROL",    SCREEN_MENU_CHANGELOG_040, SCREEN_MENU_PAGE_CHANGELOG },
    { "0.3.0 v53", "MENU BUSY GATE",     SCREEN_MENU_CHANGELOG_030, SCREEN_MENU_PAGE_CHANGELOG },
    { "0.2.0 v40", "SHELL LOG HUD CORE", SCREEN_MENU_CHANGELOG_020, SCREEN_MENU_PAGE_CHANGELOG },
    { "0.1.0 v1",  "NATIVE INIT ORIGIN", SCREEN_MENU_CHANGELOG_010, SCREEN_MENU_PAGE_CHANGELOG },
    { "BACK",      "ABOUT",              SCREEN_MENU_BACK,           SCREEN_MENU_PAGE_ABOUT },
};

static const struct screen_menu_item screen_menu_monitoring_items[] = {
    { "LIVE STATUS", "DRAW STATUS HUD", SCREEN_MENU_STATUS, SCREEN_MENU_PAGE_MONITORING },
    { "BACK",        "APPS",            SCREEN_MENU_BACK,   SCREEN_MENU_PAGE_APPS },
};

static const struct screen_menu_item screen_menu_tools_items[] = {
    { "INPUT MONITOR", "RAW KEY + GESTURE LOG", SCREEN_MENU_INPUT_MONITOR, SCREEN_MENU_PAGE_TOOLS },
    { "DISPLAY TEST",  "COLORS FONT GRID",      SCREEN_MENU_DISPLAY_TEST,  SCREEN_MENU_PAGE_TOOLS },
    { "CUTOUT CAL",    "ALIGN CAMERA HOLE",     SCREEN_MENU_CUTOUT_CAL,   SCREEN_MENU_PAGE_TOOLS },
    { "CPU STRESS >", "SELECT TEST TIME", SCREEN_MENU_SUBMENU, SCREEN_MENU_PAGE_CPU_STRESS },
    { "BACK",         "APPS",             SCREEN_MENU_BACK,    SCREEN_MENU_PAGE_APPS },
};

static const struct screen_menu_item screen_menu_cpu_stress_items[] = {
    { "5 SECONDS",  "QUICK CHECK",     SCREEN_MENU_CPU_STRESS_5,  SCREEN_MENU_PAGE_CPU_STRESS },
    { "10 SECONDS", "DEFAULT CHECK",   SCREEN_MENU_CPU_STRESS_10, SCREEN_MENU_PAGE_CPU_STRESS },
    { "30 SECONDS", "THERMAL SAMPLE",  SCREEN_MENU_CPU_STRESS_30, SCREEN_MENU_PAGE_CPU_STRESS },
    { "60 SECONDS", "LONGER SAMPLE",   SCREEN_MENU_CPU_STRESS_60, SCREEN_MENU_PAGE_CPU_STRESS },
    { "BACK",       "TOOLS",           SCREEN_MENU_BACK,          SCREEN_MENU_PAGE_TOOLS },
};

static const struct screen_menu_item screen_menu_logs_items[] = {
    { "LOG SUMMARY", "BOOT/COMMAND LOG", SCREEN_MENU_LOG,  SCREEN_MENU_PAGE_LOGS },
    { "BACK",        "APPS",             SCREEN_MENU_BACK, SCREEN_MENU_PAGE_APPS },
};

static const struct screen_menu_item screen_menu_network_items[] = {
    { "NET STATUS", "NCM/TCPCTL STATE", SCREEN_MENU_NET_STATUS, SCREEN_MENU_PAGE_NETWORK },
    { "BACK",       "MAIN MENU",        SCREEN_MENU_BACK,       SCREEN_MENU_PAGE_MAIN },
};

static const struct screen_menu_item screen_menu_power_items[] = {
    { "RECOVERY", "REBOOT TO TWRP", SCREEN_MENU_RECOVERY, SCREEN_MENU_PAGE_POWER },
    { "REBOOT",   "RESTART DEVICE", SCREEN_MENU_REBOOT,   SCREEN_MENU_PAGE_POWER },
    { "POWEROFF", "POWER OFF",      SCREEN_MENU_POWEROFF, SCREEN_MENU_PAGE_POWER },
    { "BACK",     "MAIN MENU",      SCREEN_MENU_BACK,     SCREEN_MENU_PAGE_MAIN },
};

static const struct screen_menu_page screen_menu_pages[SCREEN_MENU_PAGE_COUNT] = {
    [SCREEN_MENU_PAGE_MAIN] = {
        "MAIN MENU", screen_menu_main_items,
        SCREEN_MENU_COUNT(screen_menu_main_items), SCREEN_MENU_PAGE_MAIN
    },
    [SCREEN_MENU_PAGE_APPS] = {
        "APPS", screen_menu_apps_items,
        SCREEN_MENU_COUNT(screen_menu_apps_items), SCREEN_MENU_PAGE_MAIN
    },
    [SCREEN_MENU_PAGE_ABOUT] = {
        "APPS / ABOUT", screen_menu_about_items,
        SCREEN_MENU_COUNT(screen_menu_about_items), SCREEN_MENU_PAGE_APPS
    },
    [SCREEN_MENU_PAGE_CHANGELOG] = {
        "ABOUT / CHANGELOG", screen_menu_changelog_items,
        SCREEN_MENU_COUNT(screen_menu_changelog_items), SCREEN_MENU_PAGE_ABOUT
    },
    [SCREEN_MENU_PAGE_MONITORING] = {
        "APPS / MONITORING", screen_menu_monitoring_items,
        SCREEN_MENU_COUNT(screen_menu_monitoring_items), SCREEN_MENU_PAGE_APPS
    },
    [SCREEN_MENU_PAGE_TOOLS] = {
        "APPS / TOOLS", screen_menu_tools_items,
        SCREEN_MENU_COUNT(screen_menu_tools_items), SCREEN_MENU_PAGE_APPS
    },
    [SCREEN_MENU_PAGE_CPU_STRESS] = {
        "TOOLS / CPU STRESS", screen_menu_cpu_stress_items,
        SCREEN_MENU_COUNT(screen_menu_cpu_stress_items), SCREEN_MENU_PAGE_TOOLS
    },
    [SCREEN_MENU_PAGE_LOGS] = {
        "APPS / LOGS", screen_menu_logs_items,
        SCREEN_MENU_COUNT(screen_menu_logs_items), SCREEN_MENU_PAGE_APPS
    },
    [SCREEN_MENU_PAGE_NETWORK] = {
        "NETWORK", screen_menu_network_items,
        SCREEN_MENU_COUNT(screen_menu_network_items), SCREEN_MENU_PAGE_MAIN
    },
    [SCREEN_MENU_PAGE_POWER] = {
        "POWER", screen_menu_power_items,
        SCREEN_MENU_COUNT(screen_menu_power_items), SCREEN_MENU_PAGE_MAIN
    },
};

static const struct screen_menu_page *screen_menu_get_page(enum screen_menu_page_id page_id) {
    if ((int)page_id < 0 || page_id >= SCREEN_MENU_PAGE_COUNT) {
        page_id = SCREEN_MENU_PAGE_MAIN;
    }
    return &screen_menu_pages[page_id];
}

static long screen_menu_cpu_stress_seconds(enum screen_menu_action action) {
    switch (action) {
    case SCREEN_MENU_CPU_STRESS_5:
        return 5;
    case SCREEN_MENU_CPU_STRESS_10:
        return 10;
    case SCREEN_MENU_CPU_STRESS_30:
        return 30;
    case SCREEN_MENU_CPU_STRESS_60:
        return 60;
    default:
        return 0;
    }
}

static enum screen_app_id screen_menu_about_app(enum screen_menu_action action) {
    switch (action) {
    case SCREEN_MENU_ABOUT_VERSION:
        return SCREEN_APP_ABOUT_VERSION;
    case SCREEN_MENU_ABOUT_CHANGELOG:
        return SCREEN_APP_ABOUT_CHANGELOG;
    case SCREEN_MENU_ABOUT_CREDITS:
        return SCREEN_APP_ABOUT_CREDITS;
    case SCREEN_MENU_CHANGELOG_0815:
        return SCREEN_APP_CHANGELOG_0815;
    case SCREEN_MENU_CHANGELOG_0814:
        return SCREEN_APP_CHANGELOG_0814;
    case SCREEN_MENU_CHANGELOG_0813:
        return SCREEN_APP_CHANGELOG_0813;
    case SCREEN_MENU_CHANGELOG_0812:
        return SCREEN_APP_CHANGELOG_0812;
    case SCREEN_MENU_CHANGELOG_0811:
        return SCREEN_APP_CHANGELOG_0811;
    case SCREEN_MENU_CHANGELOG_0810:
        return SCREEN_APP_CHANGELOG_0810;
    case SCREEN_MENU_CHANGELOG_089:
        return SCREEN_APP_CHANGELOG_089;
    case SCREEN_MENU_CHANGELOG_088:
        return SCREEN_APP_CHANGELOG_088;
    case SCREEN_MENU_CHANGELOG_087:
        return SCREEN_APP_CHANGELOG_087;
    case SCREEN_MENU_CHANGELOG_086:
        return SCREEN_APP_CHANGELOG_086;
    case SCREEN_MENU_CHANGELOG_085:
        return SCREEN_APP_CHANGELOG_085;
    case SCREEN_MENU_CHANGELOG_084:
        return SCREEN_APP_CHANGELOG_084;
    case SCREEN_MENU_CHANGELOG_083:
        return SCREEN_APP_CHANGELOG_083;
    case SCREEN_MENU_CHANGELOG_082:
        return SCREEN_APP_CHANGELOG_082;
    case SCREEN_MENU_CHANGELOG_081:
        return SCREEN_APP_CHANGELOG_081;
    case SCREEN_MENU_CHANGELOG_080:
        return SCREEN_APP_CHANGELOG_080;
    case SCREEN_MENU_CHANGELOG_075:
        return SCREEN_APP_CHANGELOG_075;
    case SCREEN_MENU_CHANGELOG_074:
        return SCREEN_APP_CHANGELOG_074;
    case SCREEN_MENU_CHANGELOG_073:
        return SCREEN_APP_CHANGELOG_073;
    case SCREEN_MENU_CHANGELOG_072:
        return SCREEN_APP_CHANGELOG_072;
    case SCREEN_MENU_CHANGELOG_071:
        return SCREEN_APP_CHANGELOG_071;
    case SCREEN_MENU_CHANGELOG_070:
        return SCREEN_APP_CHANGELOG_070;
    case SCREEN_MENU_CHANGELOG_060:
        return SCREEN_APP_CHANGELOG_060;
    case SCREEN_MENU_CHANGELOG_051:
        return SCREEN_APP_CHANGELOG_051;
    case SCREEN_MENU_CHANGELOG_050:
        return SCREEN_APP_CHANGELOG_050;
    case SCREEN_MENU_CHANGELOG_041:
        return SCREEN_APP_CHANGELOG_041;
    case SCREEN_MENU_CHANGELOG_040:
        return SCREEN_APP_CHANGELOG_040;
    case SCREEN_MENU_CHANGELOG_030:
        return SCREEN_APP_CHANGELOG_030;
    case SCREEN_MENU_CHANGELOG_020:
        return SCREEN_APP_CHANGELOG_020;
    case SCREEN_MENU_CHANGELOG_010:
        return SCREEN_APP_CHANGELOG_010;
    default:
        return SCREEN_APP_NONE;
    }
}

static int draw_screen_about_app(enum screen_app_id app_id) {
    switch (app_id) {
    case SCREEN_APP_ABOUT_VERSION:
        return draw_screen_about_version();
    case SCREEN_APP_ABOUT_CHANGELOG:
        return draw_screen_about_changelog();
    case SCREEN_APP_ABOUT_CREDITS:
        return draw_screen_about_credits();
    case SCREEN_APP_CHANGELOG_0815:
    case SCREEN_APP_CHANGELOG_0814:
    case SCREEN_APP_CHANGELOG_0813:
    case SCREEN_APP_CHANGELOG_0812:
    case SCREEN_APP_CHANGELOG_0811:
    case SCREEN_APP_CHANGELOG_0810:
    case SCREEN_APP_CHANGELOG_089:
    case SCREEN_APP_CHANGELOG_088:
    case SCREEN_APP_CHANGELOG_087:
    case SCREEN_APP_CHANGELOG_086:
    case SCREEN_APP_CHANGELOG_085:
    case SCREEN_APP_CHANGELOG_084:
    case SCREEN_APP_CHANGELOG_083:
    case SCREEN_APP_CHANGELOG_082:
    case SCREEN_APP_CHANGELOG_081:
    case SCREEN_APP_CHANGELOG_080:
    case SCREEN_APP_CHANGELOG_075:
    case SCREEN_APP_CHANGELOG_074:
    case SCREEN_APP_CHANGELOG_073:
    case SCREEN_APP_CHANGELOG_072:
    case SCREEN_APP_CHANGELOG_071:
    case SCREEN_APP_CHANGELOG_070:
    case SCREEN_APP_CHANGELOG_060:
    case SCREEN_APP_CHANGELOG_051:
    case SCREEN_APP_CHANGELOG_050:
    case SCREEN_APP_CHANGELOG_041:
    case SCREEN_APP_CHANGELOG_040:
    case SCREEN_APP_CHANGELOG_030:
    case SCREEN_APP_CHANGELOG_020:
    case SCREEN_APP_CHANGELOG_010:
        return draw_screen_changelog_detail(app_id);
    default:
        return 0;
    }
}

static void screen_app_reset_stress_pids(pid_t *pids, unsigned int workers) {
    unsigned int index;

    for (index = 0; index < workers; ++index) {
        pids[index] = -1;
    }
}

static int screen_app_start_cpu_stress(pid_t *pids,
                                       unsigned int workers,
                                       long deadline_ms,
                                       unsigned int *running) {
    unsigned int index;

    screen_app_reset_stress_pids(pids, workers);
    *running = 0;
    for (index = 0; index < workers; ++index) {
        pid_t pid = fork();

        if (pid < 0) {
            int saved_errno = errno;

            cpustress_stop_workers(pids, workers);
            *running = 0;
            return -saved_errno;
        }
        if (pid == 0) {
            cpustress_worker(deadline_ms, index);
        }
        pids[index] = pid;
        ++*running;
    }
    return 0;
}

static void screen_app_read_cpu_freq_label(unsigned int cpu,
                                           char *out,
                                           size_t out_size) {
    char path[PATH_MAX];
    long khz;

    snprintf(out, out_size, "?");
    if (snprintf(path, sizeof(path),
                 "/sys/devices/system/cpu/cpu%u/cpufreq/scaling_cur_freq",
                 cpu) >= (int)sizeof(path)) {
        return;
    }
    if (read_long_value(path, &khz) < 0) {
        if (snprintf(path, sizeof(path),
                     "/sys/devices/system/cpu/cpu%u/cpufreq/cpuinfo_cur_freq",
                     cpu) >= (int)sizeof(path) ||
            read_long_value(path, &khz) < 0) {
            return;
        }
    }
    if (khz >= 1000000) {
        long tenths = (khz + 50000) / 100000;
        snprintf(out, out_size, "%ld.%ldG", tenths / 10, tenths % 10);
    } else {
        snprintf(out, out_size, "%ldM", (khz + 500) / 1000);
    }
}

static void screen_app_reap_cpu_stress(pid_t *pids,
                                       unsigned int workers,
                                       unsigned int *running) {
    unsigned int index;

    for (index = 0; index < workers; ++index) {
        if (pids[index] > 0) {
            int status;
            pid_t got = waitpid(pids[index], &status, WNOHANG);

            if (got == pids[index]) {
                pids[index] = -1;
                if (*running > 0) {
                    --*running;
                }
            }
        }
    }
}

static void auto_hud_loop(unsigned int refresh_sec) {
    struct key_wait_context ctx;
    bool menu_active = true;
    enum screen_app_id active_app = SCREEN_APP_NONE;
    enum screen_menu_page_id current_page = SCREEN_MENU_PAGE_MAIN;
    size_t menu_sel = 0;
    pid_t app_stress_pids[8];
    unsigned int app_stress_workers = 8;
    unsigned int app_stress_running = 0;
    long app_stress_deadline_ms = 0;
    long app_stress_duration_ms = 10000L;
    bool app_stress_done = false;
    bool app_stress_failed = false;
    unsigned int display_test_page = 0;
    struct cutout_calibration_state cutout_cal;
    unsigned int cutout_down_mask = 0;
    long cutout_power_down_ms = 0;
    long cutout_last_power_up_ms = 0;
    bool has_input;
    int timeout_ms;

    signal(SIGTERM, SIG_DFL);
    has_input = (open_key_wait_context(&ctx, "autohud") == 0);
    timeout_ms = (refresh_sec > 0 && refresh_sec <= 60) ? (int)(refresh_sec * 1000) : 2000;
    screen_app_reset_stress_pids(app_stress_pids, app_stress_workers);
    cutout_calibration_init(&cutout_cal);
    set_auto_menu_active(menu_active);

    while (1) {
        struct pollfd fds[2];
        int poll_rc;
        int fi;

        if (consume_auto_menu_hide_request()) {
            if (active_app == SCREEN_APP_CPU_STRESS && app_stress_running > 0) {
                cpustress_stop_workers(app_stress_pids, app_stress_workers);
                app_stress_running = 0;
            }
            active_app = SCREEN_APP_NONE;
            menu_active = false;
            current_page = SCREEN_MENU_PAGE_MAIN;
            menu_sel = 0;
            display_test_page = 0;
            cutout_calibration_init(&cutout_cal);
            cutout_down_mask = 0;
            cutout_power_down_ms = 0;
            cutout_last_power_up_ms = 0;
        }
        set_auto_menu_state(menu_active || active_app != SCREEN_APP_NONE,
                            menu_active &&
                            active_app == SCREEN_APP_NONE &&
                            current_page == SCREEN_MENU_PAGE_POWER);
        if (active_app == SCREEN_APP_INPUT_MONITOR) {
            input_monitor_app_tick();
        }

        /* draw */
        if (active_app == SCREEN_APP_LOG) {
            draw_screen_log_summary();
        } else if (active_app == SCREEN_APP_NETWORK) {
            draw_screen_network_summary();
        } else if (active_app == SCREEN_APP_INPUT_MONITOR) {
            draw_screen_input_monitor_app();
        } else if (active_app == SCREEN_APP_DISPLAY_TEST) {
            draw_screen_display_test_page(display_test_page);
        } else if (active_app == SCREEN_APP_CUTOUT_CAL) {
            draw_screen_cutout_calibration(&cutout_cal, true);
        } else if (active_app == SCREEN_APP_ABOUT_VERSION ||
                   active_app == SCREEN_APP_ABOUT_CHANGELOG ||
                   active_app == SCREEN_APP_ABOUT_CREDITS ||
                   active_app == SCREEN_APP_CHANGELOG_0815 ||
                   active_app == SCREEN_APP_CHANGELOG_0814 ||
                   active_app == SCREEN_APP_CHANGELOG_0813 ||
                   active_app == SCREEN_APP_CHANGELOG_0812 ||
                   active_app == SCREEN_APP_CHANGELOG_0811 ||
                   active_app == SCREEN_APP_CHANGELOG_0810 ||
                   active_app == SCREEN_APP_CHANGELOG_089 ||
                   active_app == SCREEN_APP_CHANGELOG_088 ||
                   active_app == SCREEN_APP_CHANGELOG_087 ||
                   active_app == SCREEN_APP_CHANGELOG_086 ||
                   active_app == SCREEN_APP_CHANGELOG_085 ||
                   active_app == SCREEN_APP_CHANGELOG_084 ||
                   active_app == SCREEN_APP_CHANGELOG_083 ||
                   active_app == SCREEN_APP_CHANGELOG_082 ||
                   active_app == SCREEN_APP_CHANGELOG_081 ||
                   active_app == SCREEN_APP_CHANGELOG_080 ||
                   active_app == SCREEN_APP_CHANGELOG_075 ||
                   active_app == SCREEN_APP_CHANGELOG_074 ||
                   active_app == SCREEN_APP_CHANGELOG_073 ||
                   active_app == SCREEN_APP_CHANGELOG_072 ||
                   active_app == SCREEN_APP_CHANGELOG_071 ||
                   active_app == SCREEN_APP_CHANGELOG_070 ||
                   active_app == SCREEN_APP_CHANGELOG_060 ||
                   active_app == SCREEN_APP_CHANGELOG_051 ||
                   active_app == SCREEN_APP_CHANGELOG_050 ||
                   active_app == SCREEN_APP_CHANGELOG_041 ||
                   active_app == SCREEN_APP_CHANGELOG_040 ||
                   active_app == SCREEN_APP_CHANGELOG_030 ||
                   active_app == SCREEN_APP_CHANGELOG_020 ||
                   active_app == SCREEN_APP_CHANGELOG_010) {
            draw_screen_about_app(active_app);
        } else if (active_app == SCREEN_APP_CPU_STRESS) {
            long now_ms = monotonic_millis();
            long remaining_ms = app_stress_deadline_ms - now_ms;

            screen_app_reap_cpu_stress(app_stress_pids,
                                       app_stress_workers,
                                       &app_stress_running);
            if (app_stress_running == 0 && !app_stress_failed) {
                app_stress_done = true;
            } else if (app_stress_running > 0 && now_ms > app_stress_deadline_ms + 2000L) {
                cpustress_stop_workers(app_stress_pids, app_stress_workers);
                app_stress_running = 0;
                app_stress_done = true;
                app_stress_failed = true;
            }
            if (remaining_ms < 0) {
                remaining_ms = 0;
            }
            draw_screen_cpu_stress_app(app_stress_running > 0,
                                       app_stress_done,
                                       app_stress_failed,
                                       remaining_ms,
                                       app_stress_duration_ms);
        } else if (kms_begin_frame(0x000000) == 0) {
            const struct screen_menu_page *page = screen_menu_get_page(current_page);

            kms_draw_status_overlay(&kms_state, 0, 0);
            if (menu_active)
                kms_draw_menu_section(&kms_state, page, menu_sel);
            else
                kms_draw_hud_log_tail(&kms_state);
            kms_present_frame_verbose("autohud", false);
        }

        if (!has_input) {
            sleep(refresh_sec);
            continue;
        }

        fds[0].fd = ctx.fd0; fds[0].events = POLLIN;
        fds[1].fd = ctx.fd3; fds[1].events = POLLIN;
        poll_rc = poll(fds, 2, active_app == SCREEN_APP_NONE ? timeout_ms : 500);
        if (poll_rc <= 0)
            continue; /* timeout → redraw */

        for (fi = 0; fi < 2; fi++) {
            struct input_event ev;
            if (!(fds[fi].revents & POLLIN))
                continue;
            while (read(fds[fi].fd, &ev, sizeof(ev)) == (ssize_t)sizeof(ev)) {
                if (active_app == SCREEN_APP_INPUT_MONITOR && ev.type == EV_KEY) {
                    if (input_monitor_app_feed_event(&ev, fi)) {
                        active_app = SCREEN_APP_NONE;
                        menu_active = true;
                        set_auto_menu_active(true);
                    }
                    continue;
                }

                if (active_app == SCREEN_APP_CUTOUT_CAL && ev.type == EV_KEY) {
                    if (cutout_calibration_feed_key(&cutout_cal,
                                                    &ev,
                                                    &cutout_down_mask,
                                                    &cutout_power_down_ms,
                                                    &cutout_last_power_up_ms)) {
                        active_app = SCREEN_APP_NONE;
                        menu_active = true;
                        set_auto_menu_active(true);
                        cutout_down_mask = 0;
                        cutout_power_down_ms = 0;
                        cutout_last_power_up_ms = 0;
                    }
                    continue;
                }

                if (ev.type != EV_KEY || ev.value != 1)
                    continue;

                if (active_app != SCREEN_APP_NONE) {
                    if (active_app == SCREEN_APP_DISPLAY_TEST) {
                        if (ev.code == KEY_VOLUMEUP) {
                            display_test_page =
                                (display_test_page + DISPLAY_TEST_PAGE_COUNT - 1) %
                                DISPLAY_TEST_PAGE_COUNT;
                            continue;
                        }
                        if (ev.code == KEY_VOLUMEDOWN) {
                            display_test_page =
                                (display_test_page + 1) % DISPLAY_TEST_PAGE_COUNT;
                            continue;
                        }
                    }
                    if (active_app == SCREEN_APP_CPU_STRESS && app_stress_running > 0) {
                        cpustress_stop_workers(app_stress_pids, app_stress_workers);
                        app_stress_running = 0;
                    }
                    active_app = SCREEN_APP_NONE;
                    menu_active = true;
                    set_auto_menu_active(true);
                    continue;
                }

                if (ev.code == KEY_VOLUMEUP) {
                    const struct screen_menu_page *page = screen_menu_get_page(current_page);

                    if (!menu_active) {
                        menu_active = true;
                        current_page = SCREEN_MENU_PAGE_MAIN;
                        menu_sel = 0;
                    } else {
                        menu_sel = (menu_sel + page->count - 1) % page->count;
                    }
                } else if (ev.code == KEY_VOLUMEDOWN) {
                    const struct screen_menu_page *page = screen_menu_get_page(current_page);

                    if (!menu_active) {
                        menu_active = true;
                        current_page = SCREEN_MENU_PAGE_MAIN;
                        menu_sel = 0;
                    } else {
                        menu_sel = (menu_sel + 1) % page->count;
                    }
                } else if (ev.code == KEY_POWER && menu_active) {
                    const struct screen_menu_page *page = screen_menu_get_page(current_page);
                    const struct screen_menu_item *item = &page->items[menu_sel];

                    switch (item->action) {
                    case SCREEN_MENU_RESUME:
                        menu_active = false;
                        current_page = SCREEN_MENU_PAGE_MAIN;
                        menu_sel = 0;
                        set_auto_menu_active(false);
                        break;
                    case SCREEN_MENU_SUBMENU:
                        current_page = item->target;
                        menu_sel = 0;
                        break;
                    case SCREEN_MENU_BACK:
                        current_page = page->parent;
                        menu_sel = 0;
                        break;
                    case SCREEN_MENU_STATUS:
                        cmd_statushud();
                        menu_active = false;
                        set_auto_menu_active(false);
                        break;
                    case SCREEN_MENU_LOG:
                        active_app = SCREEN_APP_LOG;
                        menu_active = false;
                        break;
                    case SCREEN_MENU_NET_STATUS:
                        active_app = SCREEN_APP_NETWORK;
                        menu_active = false;
                        break;
                    case SCREEN_MENU_INPUT_MONITOR:
                        input_monitor_app_reset();
                        active_app = SCREEN_APP_INPUT_MONITOR;
                        menu_active = false;
                        break;
                    case SCREEN_MENU_DISPLAY_TEST:
                        display_test_page = 0;
                        active_app = SCREEN_APP_DISPLAY_TEST;
                        menu_active = false;
                        break;
                    case SCREEN_MENU_CUTOUT_CAL:
                        cutout_calibration_init(&cutout_cal);
                        cutout_down_mask = 0;
                        cutout_power_down_ms = 0;
                        cutout_last_power_up_ms = 0;
                        active_app = SCREEN_APP_CUTOUT_CAL;
                        menu_active = false;
                        break;
                    case SCREEN_MENU_ABOUT_VERSION:
                    case SCREEN_MENU_ABOUT_CHANGELOG:
                    case SCREEN_MENU_ABOUT_CREDITS:
                    case SCREEN_MENU_CHANGELOG_0815:
                    case SCREEN_MENU_CHANGELOG_0814:
                    case SCREEN_MENU_CHANGELOG_0813:
                    case SCREEN_MENU_CHANGELOG_0812:
                    case SCREEN_MENU_CHANGELOG_0811:
                    case SCREEN_MENU_CHANGELOG_0810:
                    case SCREEN_MENU_CHANGELOG_089:
                    case SCREEN_MENU_CHANGELOG_088:
                    case SCREEN_MENU_CHANGELOG_087:
                    case SCREEN_MENU_CHANGELOG_086:
                    case SCREEN_MENU_CHANGELOG_085:
                    case SCREEN_MENU_CHANGELOG_084:
                    case SCREEN_MENU_CHANGELOG_083:
                    case SCREEN_MENU_CHANGELOG_082:
                    case SCREEN_MENU_CHANGELOG_081:
                    case SCREEN_MENU_CHANGELOG_080:
                    case SCREEN_MENU_CHANGELOG_075:
                    case SCREEN_MENU_CHANGELOG_074:
                    case SCREEN_MENU_CHANGELOG_073:
                    case SCREEN_MENU_CHANGELOG_072:
                    case SCREEN_MENU_CHANGELOG_071:
                    case SCREEN_MENU_CHANGELOG_070:
                    case SCREEN_MENU_CHANGELOG_060:
                    case SCREEN_MENU_CHANGELOG_051:
                    case SCREEN_MENU_CHANGELOG_050:
                    case SCREEN_MENU_CHANGELOG_041:
                    case SCREEN_MENU_CHANGELOG_040:
                    case SCREEN_MENU_CHANGELOG_030:
                    case SCREEN_MENU_CHANGELOG_020:
                    case SCREEN_MENU_CHANGELOG_010:
                        active_app = screen_menu_about_app(item->action);
                        menu_active = false;
                        break;
                    case SCREEN_MENU_CPU_STRESS_5:
                    case SCREEN_MENU_CPU_STRESS_10:
                    case SCREEN_MENU_CPU_STRESS_30:
                    case SCREEN_MENU_CPU_STRESS_60:
                    {
                        long stress_seconds = screen_menu_cpu_stress_seconds(item->action);

                        active_app = SCREEN_APP_CPU_STRESS;
                        menu_active = false;
                        app_stress_done = false;
                        app_stress_failed = false;
                        app_stress_duration_ms = stress_seconds * 1000L;
                        app_stress_deadline_ms = monotonic_millis() + app_stress_duration_ms;
                        if (screen_app_start_cpu_stress(app_stress_pids,
                                                        app_stress_workers,
                                                        app_stress_deadline_ms,
                                                        &app_stress_running) < 0) {
                            app_stress_failed = true;
                            app_stress_done = true;
                        }
                        break;
                    }
                    case SCREEN_MENU_RECOVERY:
                        set_auto_menu_active(false);
                        unlink(AUTO_MENU_REQUEST_PATH);
                        close_key_wait_context(&ctx);
                        cmd_recovery();
                        return;
                    case SCREEN_MENU_REBOOT:
                        set_auto_menu_active(false);
                        unlink(AUTO_MENU_REQUEST_PATH);
                        close_key_wait_context(&ctx);
                        sync();
                        reboot(RB_AUTOBOOT);
                        return;
                    case SCREEN_MENU_POWEROFF:
                        set_auto_menu_active(false);
                        unlink(AUTO_MENU_REQUEST_PATH);
                        close_key_wait_context(&ctx);
                        sync();
                        reboot(RB_POWER_OFF);
                        return;
                    }
                }
            }
        }
    }
}

static int start_auto_hud(int refresh_sec, bool verbose) {
    int saved_errno;

    refresh_sec = clamp_hud_refresh(refresh_sec);

    stop_auto_hud(false);
    unlink(AUTO_MENU_REQUEST_PATH);
    set_auto_menu_active(true);

    hud_pid = fork();
    if (hud_pid < 0) {
        saved_errno = errno;
        clear_auto_menu_ipc();
        if (verbose) {
            a90_console_printf("autohud: fork: %s\r\n", strerror(saved_errno));
        }
        hud_pid = -1;
        return -saved_errno;
    }
    if (hud_pid == 0) {
        auto_hud_loop((unsigned int)refresh_sec);
        _exit(0);
    }

    if (verbose) {
        a90_console_printf("autohud: pid=%ld refresh=%ds\r\n", (long)hud_pid, refresh_sec);
    }
    return 0;
}

static int cmd_autohud(char **argv, int argc) {
    int refresh_sec = 2;

    if (argc >= 2 && sscanf(argv[1], "%d", &refresh_sec) != 1) {
        a90_console_printf("usage: autohud [sec]\r\n");
        return -EINVAL;
    }

    return start_auto_hud(refresh_sec, true);
}

static int cmd_stophud(void) {
    stop_auto_hud(true);
    return 0;
}

static int cmd_clear_display(void) {
    stop_auto_hud(false);
    if (kms_begin_frame(0x000000) < 0) {
        return negative_errno_or(ENODEV);
    }
    if (kms_present_frame("clear") < 0) {
        return negative_errno_or(EIO);
    }
    return 0;
}

static void kms_draw_text_fit(struct kms_display_state *state,
                              uint32_t x,
                              uint32_t y,
                              const char *text,
                              uint32_t color,
                              uint32_t scale,
                              uint32_t max_width) {
    kms_draw_text(state, x, y, text, color, shrink_text_scale(text, scale, max_width));
}

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

static void kms_draw_boot_splash(struct kms_display_state *state) {
    uint32_t width = state->width;
    uint32_t height = state->height;
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

    kms_fill_color(state, 0x020713);
    kms_fill_rect(state, 0, 0, width, height / 36, 0x0b2a55);
    kms_fill_rect(state, 0, height - height / 60, width, height / 60, 0x0088cc);
    kms_fill_rect(state, x, y - scale * 3, card_w, scale * 2, 0x0088cc);

    kms_draw_text_fit(state, x, y, "A90 NATIVE INIT", 0xffffff, title_scale, card_w);
    y += title_scale * 10;
    kms_draw_text_fit(state, x, y, INIT_BANNER, 0xffcc33, scale, card_w);
    y += line_h;
    kms_draw_text_fit(state, x, y, INIT_CREATOR, 0x88ee88, scale, card_w);

    card_y = y + line_h + scale * 5;
    kms_fill_rect(state,
                  x - scale,
                  card_y - scale,
                  card_w,
                  row_gap * BOOT_SPLASH_LINE_COUNT + scale * 2,
                  0x101820);
    kms_fill_rect(state,
                  x - scale,
                  card_y - scale,
                  scale * 2,
                  row_gap * BOOT_SPLASH_LINE_COUNT + scale * 2,
                  0xffcc33);

    row_y = card_y + scale;
    row_x = x + scale * 4;
    row_w = width - row_x - x;
    for (index = 0; index < BOOT_SPLASH_LINE_COUNT; ++index) {
        kms_draw_text_fit(state,
                          row_x,
                          row_y + row_gap * (uint32_t)index,
                          boot_splash_lines[index],
                          boot_splash_line_color(boot_splash_lines[index]),
                          scale,
                          row_w);
    }

    kms_draw_text_fit(state,
                      x,
                      height - footer_scale * 16,
                      "VOL KEYS OPEN MENU AFTER BOOT",
                      0xbbbbbb,
                      footer_scale,
                      card_w);
}

static void boot_auto_frame(void) {
    if (kms_begin_frame(0x000000) == 0) {
        kms_draw_boot_splash(&kms_state);
        if (kms_present_frame("bootframe") == 0) {
            klogf("<6>A90v84: boot splash applied\n");
            if (!boot_splash_recorded) {
                boot_splash_recorded = true;
                a90_logf("boot", "display boot splash applied");
                a90_timeline_record(0, 0, "display-splash", "boot splash applied");
            }
        }
    } else {
        int saved_errno = errno;

        klogf("<6>A90v84: boot splash skipped (%d)\n", saved_errno);
        if (!boot_splash_recorded) {
            boot_splash_recorded = true;
            a90_logf("boot", "display boot splash skipped errno=%d error=%s",
                        saved_errno, strerror(saved_errno));
            a90_timeline_record(-saved_errno,
                            saved_errno,
                            "display-splash",
                            "boot splash skipped: %s",
                            strerror(saved_errno));
        }
    }
}

static bool test_key_bit(const char *bitmap, unsigned int code) {
    char copy[1024];
    char *tokens[32];
    char *token;
    char *saveptr = NULL;
    unsigned int bits_per_word = 64;
    unsigned int token_count = 0;
    unsigned int word_index;

    if (strlen(bitmap) >= sizeof(copy)) {
        return false;
    }

    strcpy(copy, bitmap);
    trim_newline(copy);

    for (token = strtok_r(copy, " \t", &saveptr);
         token != NULL;
         token = strtok_r(NULL, " \t", &saveptr)) {
        if (token_count >= (sizeof(tokens) / sizeof(tokens[0]))) {
            return false;
        }
        tokens[token_count++] = token;
    }

    for (word_index = 0; word_index < token_count; ++word_index) {
        unsigned long value = strtoul(tokens[token_count - 1 - word_index], NULL, 16);
        unsigned int bit_base = word_index * bits_per_word;

        if (code >= bit_base && code < bit_base + bits_per_word) {
            unsigned int bit = code - bit_base;
            return ((value >> bit) & 1UL) != 0;
        }
    }

    return false;
}

static int cmd_inputcaps(char **argv, int argc) {
    char event_name[32];
    char key_path[PATH_MAX];
    char bitmap[1024];

    if (argc < 2) {
        a90_console_printf("usage: inputcaps <eventX>\r\n");
        return -EINVAL;
    }

    if (normalize_event_name(argv[1], event_name, sizeof(event_name)) < 0) {
        a90_console_printf("inputcaps: invalid event name\r\n");
        return -EINVAL;
    }

    if (snprintf(key_path, sizeof(key_path),
                 "/sys/class/input/%s/device/capabilities/key", event_name) >=
        (int)sizeof(key_path)) {
        a90_console_printf("inputcaps: path too long\r\n");
        return -ENAMETOOLONG;
    }

    if (read_text_file(key_path, bitmap, sizeof(bitmap)) < 0) {
        a90_console_printf("inputcaps: %s: %s\r\n", event_name, strerror(errno));
        return negative_errno_or(ENOENT);
    }

    trim_newline(bitmap);
    a90_console_printf("%s key-bitmap=%s\r\n", event_name, bitmap);
    a90_console_printf("  KEY_VOLUMEDOWN(114)=%s\r\n",
            test_key_bit(bitmap, KEY_VOLUMEDOWN) ? "yes" : "no");
    a90_console_printf("  KEY_VOLUMEUP(115)=%s\r\n",
            test_key_bit(bitmap, KEY_VOLUMEUP) ? "yes" : "no");
    a90_console_printf("  KEY_POWER(116)=%s\r\n",
            test_key_bit(bitmap, KEY_POWER) ? "yes" : "no");
    return 0;
}

static int cmd_readinput(char **argv, int argc) {
    char event_name[32];
    char dev_path[PATH_MAX];
    int count = 16;
    int fd;
    int index;

    if (argc < 2) {
        a90_console_printf("usage: readinput <eventX> [count]\r\n");
        return -EINVAL;
    }

    if (normalize_event_name(argv[1], event_name, sizeof(event_name)) < 0) {
        a90_console_printf("readinput: invalid event name\r\n");
        return -EINVAL;
    }

    if (argc >= 3 && sscanf(argv[2], "%d", &count) != 1) {
        a90_console_printf("readinput: invalid count\r\n");
        return -EINVAL;
    }
    if (count <= 0) {
        count = 1;
    }

    if (get_input_event_path(event_name, dev_path, sizeof(dev_path)) < 0) {
        a90_console_printf("readinput: %s: %s\r\n", event_name, strerror(errno));
        return negative_errno_or(ENOENT);
    }

    fd = open(dev_path, O_RDONLY | O_NONBLOCK);
    if (fd < 0) {
        a90_console_printf("readinput: open %s: %s\r\n", dev_path, strerror(errno));
        return negative_errno_or(ENOENT);
    }

    a90_console_printf("readinput: waiting on %s (%d events), q/Ctrl-C cancels\r\n",
            dev_path, count);

    index = 0;
    while (index < count) {
        struct pollfd fds[2];
        int poll_rc;

        fds[0].fd = fd;
        fds[0].events = POLLIN;
        fds[0].revents = 0;
        fds[1].fd = STDIN_FILENO;
        fds[1].events = POLLIN;
        fds[1].revents = 0;

        poll_rc = poll(fds, 2, -1);
        if (poll_rc < 0) {
            if (errno == EINTR) {
                continue;
            }
            a90_console_printf("readinput: poll: %s\r\n", strerror(errno));
            close(fd);
            return negative_errno_or(EIO);
        }

        if ((fds[1].revents & POLLIN) != 0) {
            enum a90_cancel_kind cancel = a90_console_read_cancel_event();

            if (cancel != CANCEL_NONE) {
                close(fd);
                return a90_console_cancelled("readinput", cancel);
            }
        }

        if ((fds[0].revents & POLLIN) == 0) {
            continue;
        }

        while (index < count) {
            struct input_event event;
            ssize_t rd = read(fd, &event, sizeof(event));

            if (rd < 0) {
                if (errno == EAGAIN || errno == EWOULDBLOCK) {
                    break;
                }
                a90_console_printf("readinput: read: %s\r\n", strerror(errno));
                close(fd);
                return negative_errno_or(EIO);
            }
            if (rd != (ssize_t)sizeof(event)) {
                a90_console_printf("readinput: short read %ld\r\n", (long)rd);
                close(fd);
                return -EIO;
            }

            a90_console_printf("event %d: type=0x%04x code=0x%04x value=%d\r\n",
                    index,
                    event.type,
                    event.code,
                    event.value);
            ++index;
        }
        if ((fds[0].revents & (POLLERR | POLLHUP | POLLNVAL)) != 0) {
            a90_console_printf("readinput: poll error revents=0x%x\r\n", fds[0].revents);
            close(fd);
            return -EIO;
        }
    }

    close(fd);
    return 0;
}

static const char *key_name(unsigned int code) {
    switch (code) {
        case KEY_POWER:
            return "POWER";
        case KEY_VOLUMEUP:
            return "VOLUP";
        case KEY_VOLUMEDOWN:
            return "VOLDOWN";
        default:
            return NULL;
    }
}

#define INPUT_BUTTON_VOLUP   0x01u
#define INPUT_BUTTON_VOLDOWN 0x02u
#define INPUT_BUTTON_POWER   0x04u
#define INPUT_DOUBLE_CLICK_MS 350L
#define INPUT_LONG_PRESS_MS 800L
#define INPUT_PAGE_STEP 5

enum input_gesture_id {
    INPUT_GESTURE_NONE = 0,
    INPUT_GESTURE_VOLUP_CLICK,
    INPUT_GESTURE_VOLDOWN_CLICK,
    INPUT_GESTURE_POWER_CLICK,
    INPUT_GESTURE_VOLUP_DOUBLE,
    INPUT_GESTURE_VOLDOWN_DOUBLE,
    INPUT_GESTURE_POWER_DOUBLE,
    INPUT_GESTURE_VOLUP_LONG,
    INPUT_GESTURE_VOLDOWN_LONG,
    INPUT_GESTURE_POWER_LONG,
    INPUT_GESTURE_VOLUP_VOLDOWN,
    INPUT_GESTURE_VOLUP_POWER,
    INPUT_GESTURE_VOLDOWN_POWER,
    INPUT_GESTURE_ALL_BUTTONS,
};

enum input_menu_action {
    INPUT_MENU_ACTION_NONE = 0,
    INPUT_MENU_ACTION_PREV,
    INPUT_MENU_ACTION_NEXT,
    INPUT_MENU_ACTION_SELECT,
    INPUT_MENU_ACTION_BACK,
    INPUT_MENU_ACTION_HIDE,
    INPUT_MENU_ACTION_PAGE_PREV,
    INPUT_MENU_ACTION_PAGE_NEXT,
    INPUT_MENU_ACTION_STATUS,
    INPUT_MENU_ACTION_LOG,
    INPUT_MENU_ACTION_RESERVED,
};

struct input_gesture {
    enum input_gesture_id id;
    unsigned int code;
    unsigned int mask;
    unsigned int clicks;
    long duration_ms;
};

static unsigned int input_button_mask_from_key(unsigned int code) {
    switch (code) {
    case KEY_VOLUMEUP:
        return INPUT_BUTTON_VOLUP;
    case KEY_VOLUMEDOWN:
        return INPUT_BUTTON_VOLDOWN;
    case KEY_POWER:
        return INPUT_BUTTON_POWER;
    default:
        return 0;
    }
}

static unsigned int input_button_count(unsigned int mask) {
    unsigned int count = 0;

    if ((mask & INPUT_BUTTON_VOLUP) != 0) {
        ++count;
    }
    if ((mask & INPUT_BUTTON_VOLDOWN) != 0) {
        ++count;
    }
    if ((mask & INPUT_BUTTON_POWER) != 0) {
        ++count;
    }
    return count;
}

static void input_mask_text(unsigned int mask, char *buf, size_t buf_size) {
    size_t used = 0;

    if (buf_size == 0) {
        return;
    }
    buf[0] = '\0';
    if ((mask & INPUT_BUTTON_VOLUP) != 0) {
        used += snprintf(buf + used, used < buf_size ? buf_size - used : 0,
                         "%sVOLUP", used > 0 ? "+" : "");
    }
    if ((mask & INPUT_BUTTON_VOLDOWN) != 0) {
        used += snprintf(buf + used, used < buf_size ? buf_size - used : 0,
                         "%sVOLDOWN", used > 0 ? "+" : "");
    }
    if ((mask & INPUT_BUTTON_POWER) != 0) {
        used += snprintf(buf + used, used < buf_size ? buf_size - used : 0,
                         "%sPOWER", used > 0 ? "+" : "");
    }
    if (used == 0) {
        snprintf(buf, buf_size, "NONE");
    }
}

static const char *input_gesture_name(enum input_gesture_id id) {
    switch (id) {
    case INPUT_GESTURE_VOLUP_CLICK:
        return "VOLUP_CLICK";
    case INPUT_GESTURE_VOLDOWN_CLICK:
        return "VOLDOWN_CLICK";
    case INPUT_GESTURE_POWER_CLICK:
        return "POWER_CLICK";
    case INPUT_GESTURE_VOLUP_DOUBLE:
        return "VOLUP_DOUBLE";
    case INPUT_GESTURE_VOLDOWN_DOUBLE:
        return "VOLDOWN_DOUBLE";
    case INPUT_GESTURE_POWER_DOUBLE:
        return "POWER_DOUBLE";
    case INPUT_GESTURE_VOLUP_LONG:
        return "VOLUP_LONG";
    case INPUT_GESTURE_VOLDOWN_LONG:
        return "VOLDOWN_LONG";
    case INPUT_GESTURE_POWER_LONG:
        return "POWER_LONG";
    case INPUT_GESTURE_VOLUP_VOLDOWN:
        return "VOLUP+VOLDOWN";
    case INPUT_GESTURE_VOLUP_POWER:
        return "VOLUP+POWER";
    case INPUT_GESTURE_VOLDOWN_POWER:
        return "VOLDOWN+POWER";
    case INPUT_GESTURE_ALL_BUTTONS:
        return "VOLUP+VOLDOWN+POWER";
    default:
        return "NONE";
    }
}

static enum input_gesture_id input_single_gesture(unsigned int code,
                                                  unsigned int clicks,
                                                  long duration_ms) {
    if (duration_ms >= INPUT_LONG_PRESS_MS) {
        switch (code) {
        case KEY_VOLUMEUP:
            return INPUT_GESTURE_VOLUP_LONG;
        case KEY_VOLUMEDOWN:
            return INPUT_GESTURE_VOLDOWN_LONG;
        case KEY_POWER:
            return INPUT_GESTURE_POWER_LONG;
        default:
            return INPUT_GESTURE_NONE;
        }
    }
    if (clicks >= 2) {
        switch (code) {
        case KEY_VOLUMEUP:
            return INPUT_GESTURE_VOLUP_DOUBLE;
        case KEY_VOLUMEDOWN:
            return INPUT_GESTURE_VOLDOWN_DOUBLE;
        case KEY_POWER:
            return INPUT_GESTURE_POWER_DOUBLE;
        default:
            return INPUT_GESTURE_NONE;
        }
    }
    switch (code) {
    case KEY_VOLUMEUP:
        return INPUT_GESTURE_VOLUP_CLICK;
    case KEY_VOLUMEDOWN:
        return INPUT_GESTURE_VOLDOWN_CLICK;
    case KEY_POWER:
        return INPUT_GESTURE_POWER_CLICK;
    default:
        return INPUT_GESTURE_NONE;
    }
}

static enum input_gesture_id input_combo_gesture(unsigned int mask) {
    switch (mask & (INPUT_BUTTON_VOLUP | INPUT_BUTTON_VOLDOWN | INPUT_BUTTON_POWER)) {
    case INPUT_BUTTON_VOLUP | INPUT_BUTTON_VOLDOWN:
        return INPUT_GESTURE_VOLUP_VOLDOWN;
    case INPUT_BUTTON_VOLUP | INPUT_BUTTON_POWER:
        return INPUT_GESTURE_VOLUP_POWER;
    case INPUT_BUTTON_VOLDOWN | INPUT_BUTTON_POWER:
        return INPUT_GESTURE_VOLDOWN_POWER;
    case INPUT_BUTTON_VOLUP | INPUT_BUTTON_VOLDOWN | INPUT_BUTTON_POWER:
        return INPUT_GESTURE_ALL_BUTTONS;
    default:
        return INPUT_GESTURE_NONE;
    }
}

static void input_gesture_set(struct input_gesture *gesture,
                              enum input_gesture_id id,
                              unsigned int code,
                              unsigned int mask,
                              unsigned int clicks,
                              long duration_ms) {
    gesture->id = id;
    gesture->code = code;
    gesture->mask = mask;
    gesture->clicks = clicks;
    gesture->duration_ms = duration_ms;
}

struct input_decoder {
    unsigned int down_mask;
    unsigned int pressed_mask;
    unsigned int primary_code;
    unsigned int primary_mask;
    unsigned int pending_code;
    unsigned int pending_mask;
    long first_down_ms;
    long pending_up_ms;
    long pending_duration_ms;
    bool waiting_second;
    bool second_click;
};

static void input_decoder_init(struct input_decoder *decoder) {
    memset(decoder, 0, sizeof(*decoder));
}

static int input_decoder_timeout_ms(const struct input_decoder *decoder) {
    long elapsed_ms;
    long remaining_ms;

    if (!decoder->waiting_second) {
        return -1;
    }

    elapsed_ms = monotonic_millis() - decoder->pending_up_ms;
    if (elapsed_ms >= INPUT_DOUBLE_CLICK_MS) {
        return 0;
    }

    remaining_ms = INPUT_DOUBLE_CLICK_MS - elapsed_ms;
    if (remaining_ms > INT_MAX) {
        return INT_MAX;
    }
    return (int)remaining_ms;
}

static bool input_decoder_emit_pending_if_due(struct input_decoder *decoder,
                                              struct input_gesture *gesture) {
    long elapsed_ms;

    if (!decoder->waiting_second) {
        return false;
    }

    elapsed_ms = monotonic_millis() - decoder->pending_up_ms;
    if (elapsed_ms < INPUT_DOUBLE_CLICK_MS) {
        return false;
    }

    input_gesture_set(gesture,
                      input_single_gesture(decoder->pending_code,
                                           1,
                                           decoder->pending_duration_ms),
                      decoder->pending_code,
                      decoder->pending_mask,
                      1,
                      decoder->pending_duration_ms);
    decoder->waiting_second = false;
    return true;
}

static bool input_decoder_feed(struct input_decoder *decoder,
                               const struct input_event *event,
                               long now_ms,
                               struct input_gesture *gesture) {
    unsigned int mask;

    if (event->type != EV_KEY || event->value == 2) {
        return false;
    }

    mask = input_button_mask_from_key(event->code);
    if (mask == 0) {
        return false;
    }

    if (event->value == 1) {
        if (decoder->waiting_second) {
            if (mask == decoder->pending_mask &&
                decoder->down_mask == 0 &&
                now_ms - decoder->pending_up_ms <= INPUT_DOUBLE_CLICK_MS) {
                decoder->waiting_second = false;
                decoder->second_click = true;
                decoder->down_mask = mask;
                decoder->pressed_mask = mask;
                decoder->primary_code = event->code;
                decoder->primary_mask = mask;
                decoder->first_down_ms = now_ms;
            } else {
                input_gesture_set(gesture,
                                  input_single_gesture(decoder->pending_code,
                                                       1,
                                                       decoder->pending_duration_ms),
                                  decoder->pending_code,
                                  decoder->pending_mask,
                                  1,
                                  decoder->pending_duration_ms);
                decoder->waiting_second = false;
                return true;
            }
        } else if (decoder->down_mask == 0) {
            decoder->second_click = false;
            decoder->down_mask = mask;
            decoder->pressed_mask = mask;
            decoder->primary_code = event->code;
            decoder->primary_mask = mask;
            decoder->first_down_ms = now_ms;
        } else {
            decoder->down_mask |= mask;
            decoder->pressed_mask |= mask;
        }
    } else if (event->value == 0 && (decoder->down_mask & mask) != 0) {
        decoder->down_mask &= ~mask;
        if (decoder->down_mask == 0) {
            long duration_ms = now_ms - decoder->first_down_ms;
            unsigned int count = input_button_count(decoder->pressed_mask);

            if (count > 1) {
                input_gesture_set(gesture,
                                  input_combo_gesture(decoder->pressed_mask),
                                  decoder->primary_code,
                                  decoder->pressed_mask,
                                  1,
                                  duration_ms);
                decoder->pressed_mask = 0;
                return true;
            }
            if (decoder->second_click) {
                input_gesture_set(gesture,
                                  input_single_gesture(decoder->primary_code,
                                                       2,
                                                       duration_ms),
                                  decoder->primary_code,
                                  decoder->primary_mask,
                                  2,
                                  duration_ms);
                decoder->pressed_mask = 0;
                decoder->second_click = false;
                return true;
            }
            if (duration_ms >= INPUT_LONG_PRESS_MS) {
                input_gesture_set(gesture,
                                  input_single_gesture(decoder->primary_code,
                                                       1,
                                                       duration_ms),
                                  decoder->primary_code,
                                  decoder->primary_mask,
                                  1,
                                  duration_ms);
                decoder->pressed_mask = 0;
                return true;
            }
            decoder->waiting_second = true;
            decoder->pending_code = decoder->primary_code;
            decoder->pending_mask = decoder->primary_mask;
            decoder->pending_up_ms = now_ms;
            decoder->pending_duration_ms = duration_ms;
        }
    }

    return false;
}

static enum input_menu_action input_menu_action_from_gesture(
        const struct input_gesture *gesture) {
    switch (gesture->id) {
    case INPUT_GESTURE_VOLUP_CLICK:
        return INPUT_MENU_ACTION_PREV;
    case INPUT_GESTURE_VOLDOWN_CLICK:
        return INPUT_MENU_ACTION_NEXT;
    case INPUT_GESTURE_POWER_CLICK:
        return INPUT_MENU_ACTION_SELECT;
    case INPUT_GESTURE_VOLUP_DOUBLE:
    case INPUT_GESTURE_VOLUP_LONG:
        return INPUT_MENU_ACTION_PAGE_PREV;
    case INPUT_GESTURE_VOLDOWN_DOUBLE:
    case INPUT_GESTURE_VOLDOWN_LONG:
        return INPUT_MENU_ACTION_PAGE_NEXT;
    case INPUT_GESTURE_POWER_DOUBLE:
    case INPUT_GESTURE_VOLUP_VOLDOWN:
        return INPUT_MENU_ACTION_BACK;
    case INPUT_GESTURE_ALL_BUTTONS:
        return INPUT_MENU_ACTION_HIDE;
    case INPUT_GESTURE_VOLUP_POWER:
        return INPUT_MENU_ACTION_STATUS;
    case INPUT_GESTURE_VOLDOWN_POWER:
        return INPUT_MENU_ACTION_LOG;
    case INPUT_GESTURE_POWER_LONG:
        return INPUT_MENU_ACTION_RESERVED;
    default:
        return INPUT_MENU_ACTION_NONE;
    }
}

static const char *input_menu_action_name(enum input_menu_action action) {
    switch (action) {
    case INPUT_MENU_ACTION_PREV:
        return "PREVIOUS";
    case INPUT_MENU_ACTION_NEXT:
        return "NEXT";
    case INPUT_MENU_ACTION_SELECT:
        return "SELECT";
    case INPUT_MENU_ACTION_BACK:
        return "BACK";
    case INPUT_MENU_ACTION_HIDE:
        return "HIDE/EXIT";
    case INPUT_MENU_ACTION_PAGE_PREV:
        return "PAGE UP";
    case INPUT_MENU_ACTION_PAGE_NEXT:
        return "PAGE DOWN";
    case INPUT_MENU_ACTION_STATUS:
        return "STATUS";
    case INPUT_MENU_ACTION_LOG:
        return "LOG";
    case INPUT_MENU_ACTION_RESERVED:
        return "RESERVED";
    default:
        return "NONE";
    }
}

static void print_input_layout(void) {
    a90_console_printf("inputlayout: single click\r\n");
    a90_console_printf("  VOLUP    -> previous item\r\n");
    a90_console_printf("  VOLDOWN  -> next item\r\n");
    a90_console_printf("  POWER    -> select\r\n");
    a90_console_printf("inputlayout: double click / long press\r\n");
    a90_console_printf("  VOLUP    -> page previous (%d items)\r\n", INPUT_PAGE_STEP);
    a90_console_printf("  VOLDOWN  -> page next (%d items)\r\n", INPUT_PAGE_STEP);
    a90_console_printf("  POWER x2 -> back\r\n");
    a90_console_printf("  POWER long -> reserved/ignored for safety\r\n");
    a90_console_printf("inputlayout: combos\r\n");
    a90_console_printf("  VOLUP+VOLDOWN -> back\r\n");
    a90_console_printf("  VOLUP+POWER   -> status shortcut\r\n");
    a90_console_printf("  VOLDOWN+POWER -> log shortcut\r\n");
    a90_console_printf("  all buttons   -> hide/exit menu\r\n");
    a90_console_printf("timing: double=%ldms long=%ldms\r\n",
            INPUT_DOUBLE_CLICK_MS,
            INPUT_LONG_PRESS_MS);
}

static int wait_for_input_gesture(struct key_wait_context *ctx,
                                  const char *tag,
                                  struct input_gesture *gesture) {
    struct pollfd fds[3];
    struct input_decoder decoder;

    input_decoder_init(&decoder);

    fds[0].fd = ctx->fd0;
    fds[0].events = POLLIN;
    fds[1].fd = ctx->fd3;
    fds[1].events = POLLIN;
    fds[2].fd = STDIN_FILENO;
    fds[2].events = POLLIN;

    while (1) {
        int timeout_ms;
        int poll_rc;
        int index;

        if (input_decoder_emit_pending_if_due(&decoder, gesture)) {
            return 0;
        }
        timeout_ms = input_decoder_timeout_ms(&decoder);

        poll_rc = poll(fds, 3, timeout_ms);
        if (poll_rc < 0) {
            int saved_errno = errno;

            if (errno == EINTR) {
                continue;
            }
            a90_console_printf("%s: poll: %s\r\n", tag, strerror(saved_errno));
            return -saved_errno;
        }

        if (poll_rc == 0) {
            if (input_decoder_emit_pending_if_due(&decoder, gesture)) {
                return 0;
            }
            continue;
        }

        if ((fds[2].revents & POLLIN) != 0) {
            enum a90_cancel_kind cancel = a90_console_read_cancel_event();

            if (cancel != CANCEL_NONE) {
                return a90_console_cancelled(tag, cancel);
            }
        }

        for (index = 0; index < 2; ++index) {
            if (fds[index].revents & POLLIN) {
                struct input_event event;
                ssize_t rd;

                while ((rd = read(fds[index].fd, &event, sizeof(event))) ==
                       (ssize_t)sizeof(event)) {
                    long now_ms;

                    now_ms = monotonic_millis();
                    if (input_decoder_feed(&decoder, &event, now_ms, gesture)) {
                        return 0;
                    }
                }

                if (rd < 0 && errno != EAGAIN && errno != EWOULDBLOCK) {
                    int saved_errno = errno;

                    a90_console_printf("%s: read: %s\r\n", tag, strerror(saved_errno));
                    return -saved_errno;
                }
            }
            if ((fds[index].revents & (POLLERR | POLLHUP | POLLNVAL)) != 0) {
                a90_console_printf("%s: poll error revents=0x%x\r\n", tag, fds[index].revents);
                return -EIO;
            }
        }
    }
}

static int cmd_recovery(void);

static int open_key_wait_context(struct key_wait_context *ctx, const char *tag) {
    char event0_path[PATH_MAX];
    char event3_path[PATH_MAX];

    ctx->fd0 = -1;
    ctx->fd3 = -1;

    if (get_input_event_path("event0", event0_path, sizeof(event0_path)) < 0 ||
        get_input_event_path("event3", event3_path, sizeof(event3_path)) < 0) {
        a90_console_printf("%s: input node setup failed: %s\r\n", tag, strerror(errno));
        return -1;
    }

    ctx->fd0 = open(event0_path, O_RDONLY | O_NONBLOCK);
    if (ctx->fd0 < 0) {
        a90_console_printf("%s: open %s: %s\r\n", tag, event0_path, strerror(errno));
        return -1;
    }

    ctx->fd3 = open(event3_path, O_RDONLY | O_NONBLOCK);
    if (ctx->fd3 < 0) {
        a90_console_printf("%s: open %s: %s\r\n", tag, event3_path, strerror(errno));
        close(ctx->fd0);
        ctx->fd0 = -1;
        return -1;
    }

    return 0;
}

static void close_key_wait_context(struct key_wait_context *ctx) {
    if (ctx->fd0 >= 0) {
        close(ctx->fd0);
        ctx->fd0 = -1;
    }
    if (ctx->fd3 >= 0) {
        close(ctx->fd3);
        ctx->fd3 = -1;
    }
}

static int wait_for_key_press(struct key_wait_context *ctx,
                              const char *tag,
                              unsigned int *code_out) {
    struct pollfd fds[3];

    fds[0].fd = ctx->fd0;
    fds[0].events = POLLIN;
    fds[1].fd = ctx->fd3;
    fds[1].events = POLLIN;
    fds[2].fd = STDIN_FILENO;
    fds[2].events = POLLIN;

    while (1) {
        int poll_rc = poll(fds, 3, -1);
        int index;

        if (poll_rc < 0) {
            int saved_errno = errno;

            if (errno == EINTR) {
                continue;
            }
            a90_console_printf("%s: poll: %s\r\n", tag, strerror(saved_errno));
            return -saved_errno;
        }

        if ((fds[2].revents & POLLIN) != 0) {
            enum a90_cancel_kind cancel = a90_console_read_cancel_event();

            if (cancel != CANCEL_NONE) {
                return a90_console_cancelled(tag, cancel);
            }
        }

        for (index = 0; index < 2; ++index) {
            if (fds[index].revents & POLLIN) {
                struct input_event event;
                ssize_t rd;

                while ((rd = read(fds[index].fd, &event, sizeof(event))) ==
                       (ssize_t)sizeof(event)) {
                    if (event.type == EV_KEY && event.value == 1) {
                        *code_out = event.code;
                        return 0;
                    }
                }

                if (rd < 0 && errno != EAGAIN && errno != EWOULDBLOCK) {
                    int saved_errno = errno;

                    a90_console_printf("%s: read: %s\r\n", tag, strerror(saved_errno));
                    return -saved_errno;
                }
            }
            if ((fds[index].revents & (POLLERR | POLLHUP | POLLNVAL)) != 0) {
                a90_console_printf("%s: poll error revents=0x%x\r\n", tag, fds[index].revents);
                return -EIO;
            }
        }
    }
}

static int cmd_waitkey(char **argv, int argc) {
    struct key_wait_context ctx;
    int target = 1;
    int seen = 0;

    if (argc >= 2 && sscanf(argv[1], "%d", &target) != 1) {
        a90_console_printf("usage: waitkey [count]\r\n");
        return -EINVAL;
    }
    if (target <= 0) {
        target = 1;
    }

    if (open_key_wait_context(&ctx, "waitkey") < 0) {
        return negative_errno_or(ENOENT);
    }

    a90_console_printf("waitkey: waiting for %d key press(es), q/Ctrl-C cancels\r\n", target);

    while (seen < target) {
        unsigned int code = 0;
        const char *name;

        int wait_rc = wait_for_key_press(&ctx, "waitkey", &code);

        if (wait_rc < 0) {
            close_key_wait_context(&ctx);
            return wait_rc;
        }

        name = key_name(code);
        if (name != NULL) {
            a90_console_printf("key %d: %s (0x%04x)\r\n", seen, name, code);
        } else {
            a90_console_printf("key %d: code=0x%04x\r\n", seen, code);
        }
        ++seen;
    }

    close_key_wait_context(&ctx);
    return 0;
}

static int cmd_inputlayout(char **argv, int argc) {
    (void)argv;
    (void)argc;
    print_input_layout();
    return 0;
}

static int cmd_waitgesture(char **argv, int argc) {
    struct key_wait_context ctx;
    int target = 1;
    int seen = 0;

    if (argc >= 2 && sscanf(argv[1], "%d", &target) != 1) {
        a90_console_printf("usage: waitgesture [count]\r\n");
        return -EINVAL;
    }
    if (target <= 0) {
        target = 1;
    }

    if (open_key_wait_context(&ctx, "waitgesture") < 0) {
        return negative_errno_or(ENOENT);
    }

    a90_console_printf("waitgesture: waiting for %d gesture(s), q/Ctrl-C cancels\r\n", target);
    a90_console_printf("waitgesture: double=%ldms long=%ldms\r\n",
            INPUT_DOUBLE_CLICK_MS,
            INPUT_LONG_PRESS_MS);

    while (seen < target) {
        struct input_gesture gesture;
        char mask_text[64];
        int wait_rc = wait_for_input_gesture(&ctx, "waitgesture", &gesture);

        if (wait_rc < 0) {
            close_key_wait_context(&ctx);
            return wait_rc;
        }

        input_mask_text(gesture.mask, mask_text, sizeof(mask_text));
        a90_console_printf("gesture %d: %s mask=%s clicks=%u duration=%ldms action=%d\r\n",
                seen,
                input_gesture_name(gesture.id),
                mask_text,
                gesture.clicks,
                gesture.duration_ms,
                (int)input_menu_action_from_gesture(&gesture));
        ++seen;
    }

    close_key_wait_context(&ctx);
    return 0;
}

#define INPUT_MONITOR_ROWS 9

struct input_monitor_raw_entry {
    char title[64];
    char detail[96];
    int value;
};

struct input_monitor_state {
    struct input_decoder decoder;
    struct input_monitor_raw_entry raw_entries[INPUT_MONITOR_ROWS];
    char gesture_title[80];
    char gesture_detail[128];
    char gesture_mask[64];
    enum input_gesture_id gesture_id;
    enum input_menu_action gesture_action;
    unsigned int gesture_clicks;
    long gesture_duration_ms;
    long gesture_gap_ms;
    long key_down_ms[3];
    long last_raw_ms;
    long last_gesture_ms;
    unsigned int raw_head;
    unsigned int raw_count;
    unsigned int event_count;
    unsigned int gesture_count;
    bool exit_requested;
};

static struct input_monitor_state auto_input_monitor;
static int draw_screen_input_monitor_state(const struct input_monitor_state *monitor);

static int input_monitor_key_index(unsigned int code) {
    switch (code) {
    case KEY_VOLUMEUP:
        return 0;
    case KEY_VOLUMEDOWN:
        return 1;
    case KEY_POWER:
        return 2;
    default:
        return -1;
    }
}

static const char *input_monitor_value_name(int value) {
    switch (value) {
    case 0:
        return "UP";
    case 1:
        return "DOWN";
    case 2:
        return "REPEAT";
    default:
        return "VALUE";
    }
}

static void input_monitor_reset_state(struct input_monitor_state *monitor) {
    input_decoder_init(&monitor->decoder);
    memset(monitor->raw_entries, 0, sizeof(monitor->raw_entries));
    memset(monitor->gesture_title, 0, sizeof(monitor->gesture_title));
    memset(monitor->gesture_detail, 0, sizeof(monitor->gesture_detail));
    memset(monitor->gesture_mask, 0, sizeof(monitor->gesture_mask));
    memset(monitor->key_down_ms, 0, sizeof(monitor->key_down_ms));
    snprintf(monitor->gesture_title, sizeof(monitor->gesture_title),
             "GESTURE waiting");
    snprintf(monitor->gesture_detail, sizeof(monitor->gesture_detail),
             "double=%ldms long=%ldms",
             INPUT_DOUBLE_CLICK_MS,
             INPUT_LONG_PRESS_MS);
    snprintf(monitor->gesture_mask, sizeof(monitor->gesture_mask), "NONE");
    monitor->gesture_id = INPUT_GESTURE_NONE;
    monitor->gesture_action = INPUT_MENU_ACTION_NONE;
    monitor->gesture_clicks = 0;
    monitor->gesture_duration_ms = 0;
    monitor->gesture_gap_ms = -1;
    monitor->last_raw_ms = 0;
    monitor->last_gesture_ms = 0;
    monitor->raw_head = 0;
    monitor->raw_count = 0;
    monitor->event_count = 0;
    monitor->gesture_count = 0;
    monitor->exit_requested = false;
}

static void input_monitor_push_raw(struct input_monitor_state *monitor,
                                   const char *serial_line,
                                   const char *title,
                                   const char *detail,
                                   int value,
                                   bool serial_echo) {
    size_t slot = monitor->raw_head % INPUT_MONITOR_ROWS;

    snprintf(monitor->raw_entries[slot].title,
             sizeof(monitor->raw_entries[slot].title),
             "%s", title);
    snprintf(monitor->raw_entries[slot].detail,
             sizeof(monitor->raw_entries[slot].detail),
             "%s", detail);
    monitor->raw_entries[slot].value = value;
    ++monitor->raw_head;
    if (monitor->raw_count < INPUT_MONITOR_ROWS) {
        ++monitor->raw_count;
    }

    a90_logf("inputmonitor", "%s", serial_line);
    if (serial_echo) {
        a90_console_printf("inputmonitor: %s\r\n", serial_line);
    }
}

static void input_monitor_emit_gesture(struct input_monitor_state *monitor,
                                       const struct input_gesture *gesture,
                                       bool serial_echo) {
    char mask_text[64];
    long now_ms = monotonic_millis();
    long gap_ms = monitor->last_gesture_ms > 0 ?
                  now_ms - monitor->last_gesture_ms : -1;

    input_mask_text(gesture->mask, mask_text, sizeof(mask_text));
    ++monitor->gesture_count;
    monitor->gesture_id = gesture->id;
    monitor->gesture_action = input_menu_action_from_gesture(gesture);
    monitor->gesture_clicks = gesture->clicks;
    monitor->gesture_duration_ms = gesture->duration_ms;
    monitor->gesture_gap_ms = gap_ms;
    snprintf(monitor->gesture_mask, sizeof(monitor->gesture_mask),
             "%s", mask_text);
    snprintf(monitor->gesture_title, sizeof(monitor->gesture_title),
             "G%03u %s",
             monitor->gesture_count,
             input_gesture_name(gesture->id));
    snprintf(monitor->gesture_detail, sizeof(monitor->gesture_detail),
             "mask=%s click=%u dur=%ldms gap=%ldms action=%s",
             mask_text,
             gesture->clicks,
             gesture->duration_ms,
             gap_ms,
             input_menu_action_name(monitor->gesture_action));
    monitor->last_gesture_ms = now_ms;

    a90_logf("inputmonitor", "%s / %s",
                monitor->gesture_title,
                monitor->gesture_detail);
    if (serial_echo) {
        a90_console_printf("inputmonitor: %s / %s\r\n",
                monitor->gesture_title,
                monitor->gesture_detail);
    }
}

static bool input_monitor_feed_state(struct input_monitor_state *monitor,
                                     const struct input_event *event,
                                     int source_index,
                                     bool serial_echo,
                                     bool exit_on_all_buttons) {
    struct input_gesture gesture;
    char serial_line[128];
    char title[64];
    char detail[96];
    char key_label[32];
    char hold_label[24];
    const char *name;
    long now_ms;
    long gap_ms;
    long hold_ms = -1;
    int key_index;

    if (event->type != EV_KEY) {
        return false;
    }

    key_index = input_monitor_key_index(event->code);
    name = key_name(event->code);
    if (name != NULL) {
        snprintf(key_label, sizeof(key_label), "%s", name);
    } else {
        snprintf(key_label, sizeof(key_label), "KEY%u", event->code);
    }

    now_ms = monotonic_millis();
    gap_ms = monitor->last_raw_ms > 0 ? now_ms - monitor->last_raw_ms : -1;
    monitor->last_raw_ms = now_ms;

    if (key_index >= 0) {
        if (event->value == 1) {
            monitor->key_down_ms[key_index] = now_ms;
        } else if (event->value == 0 && monitor->key_down_ms[key_index] > 0) {
            hold_ms = now_ms - monitor->key_down_ms[key_index];
            monitor->key_down_ms[key_index] = 0;
        } else if (event->value == 2 && monitor->key_down_ms[key_index] > 0) {
            hold_ms = now_ms - monitor->key_down_ms[key_index];
        }
    }

    if (hold_ms >= 0) {
        snprintf(hold_label, sizeof(hold_label), "%ldms", hold_ms);
    } else {
        snprintf(hold_label, sizeof(hold_label), "-");
    }

    ++monitor->event_count;
    snprintf(title, sizeof(title),
             "R%03u %-6s %-7s event%d",
             monitor->event_count,
             input_monitor_value_name(event->value),
             key_label,
             source_index == 0 ? 0 : 3);
    snprintf(detail, sizeof(detail),
             "gap=%ldms hold=%s code=0x%04x",
             gap_ms,
             hold_label,
             event->code);
    snprintf(serial_line, sizeof(serial_line),
             "R%03u event%d %-7s %-6s gap=%ldms hold=%s",
             monitor->event_count,
             source_index == 0 ? 0 : 3,
             key_label,
             input_monitor_value_name(event->value),
             gap_ms,
             hold_label);
    input_monitor_push_raw(monitor,
                           serial_line,
                           title,
                           detail,
                           event->value,
                           serial_echo);

    if (input_decoder_feed(&monitor->decoder, event, now_ms, &gesture)) {
        input_monitor_emit_gesture(monitor, &gesture, serial_echo);
        if (exit_on_all_buttons && gesture.id == INPUT_GESTURE_ALL_BUTTONS) {
            monitor->exit_requested = true;
        }
    }

    if (exit_on_all_buttons &&
        event->value == 1 &&
        (monitor->decoder.down_mask &
         (INPUT_BUTTON_VOLUP | INPUT_BUTTON_VOLDOWN | INPUT_BUTTON_POWER)) ==
        (INPUT_BUTTON_VOLUP | INPUT_BUTTON_VOLDOWN | INPUT_BUTTON_POWER)) {
        long duration_ms = now_ms - monitor->decoder.first_down_ms;

        if (duration_ms < 0) {
            duration_ms = 0;
        }
        input_gesture_set(&gesture,
                          INPUT_GESTURE_ALL_BUTTONS,
                          event->code,
                          INPUT_BUTTON_VOLUP | INPUT_BUTTON_VOLDOWN | INPUT_BUTTON_POWER,
                          1,
                          duration_ms);
        input_monitor_emit_gesture(monitor, &gesture, serial_echo);
        monitor->exit_requested = true;
    }

    return monitor->exit_requested;
}

static void input_monitor_tick_state(struct input_monitor_state *monitor,
                                     bool serial_echo) {
    struct input_gesture gesture;

    if (input_decoder_emit_pending_if_due(&monitor->decoder, &gesture)) {
        input_monitor_emit_gesture(monitor, &gesture, serial_echo);
    }
}

static void input_monitor_app_reset(void) {
    input_monitor_reset_state(&auto_input_monitor);
    a90_logf("inputmonitor", "app reset");
}

static void input_monitor_app_tick(void) {
    input_monitor_tick_state(&auto_input_monitor, false);
}

static bool input_monitor_app_feed_event(const struct input_event *event,
                                         int source_index) {
    return input_monitor_feed_state(&auto_input_monitor,
                                    event,
                                    source_index,
                                    false,
                                    true);
}

static int cmd_inputmonitor(char **argv, int argc) {
    struct input_monitor_state monitor;
    struct key_wait_context ctx;
    int target = 24;
    int seen = 0;
    int draw_rc;

    if (argc >= 2 && sscanf(argv[1], "%d", &target) != 1) {
        a90_console_printf("usage: inputmonitor [events]\r\n");
        return -EINVAL;
    }
    if (target < 0) {
        target = 0;
    }

    reap_hud_child();
    stop_auto_hud(false);
    input_monitor_reset_state(&monitor);

    if (open_key_wait_context(&ctx, "inputmonitor") < 0) {
        restore_auto_hud_if_needed(true);
        return negative_errno_or(ENOENT);
    }

    a90_console_printf("inputmonitor: raw DOWN/UP/REPEAT + gesture decode\r\n");
    a90_console_printf("inputmonitor: events=%d, 0 means until all-buttons/q/Ctrl-C\r\n", target);
    a90_console_printf("inputmonitor: all-buttons exits only in events=0 mode\r\n");

    draw_rc = draw_screen_input_monitor_state(&monitor);
    if (draw_rc < 0) {
        close_key_wait_context(&ctx);
        restore_auto_hud_if_needed(true);
        return draw_rc;
    }

    while (target == 0 || seen < target) {
        struct pollfd fds[3];
        int timeout_ms;
        int poll_rc;
        int index;

        input_monitor_tick_state(&monitor, true);
        draw_screen_input_monitor_state(&monitor);

        fds[0].fd = ctx.fd0;
        fds[0].events = POLLIN;
        fds[0].revents = 0;
        fds[1].fd = ctx.fd3;
        fds[1].events = POLLIN;
        fds[1].revents = 0;
        fds[2].fd = STDIN_FILENO;
        fds[2].events = POLLIN;
        fds[2].revents = 0;

        timeout_ms = input_decoder_timeout_ms(&monitor.decoder);
        poll_rc = poll(fds, 3, timeout_ms);
        if (poll_rc < 0) {
            int saved_errno = errno;

            if (errno == EINTR) {
                continue;
            }
            a90_console_printf("inputmonitor: poll: %s\r\n", strerror(saved_errno));
            close_key_wait_context(&ctx);
            restore_auto_hud_if_needed(true);
            return -saved_errno;
        }

        if (poll_rc == 0) {
            continue;
        }

        if ((fds[2].revents & POLLIN) != 0) {
            enum a90_cancel_kind cancel = a90_console_read_cancel_event();

            if (cancel != CANCEL_NONE) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(true);
                return a90_console_cancelled("inputmonitor", cancel);
            }
        }

        for (index = 0; index < 2; ++index) {
            if ((fds[index].revents & POLLIN) != 0) {
                struct input_event event;
                ssize_t rd;

                while ((rd = read(fds[index].fd, &event, sizeof(event))) ==
                       (ssize_t)sizeof(event)) {
                    unsigned int before_count = monitor.event_count;

                    if (input_monitor_feed_state(&monitor,
                                                 &event,
                                                 index,
                                                 true,
                                                 target == 0)) {
                        draw_screen_input_monitor_state(&monitor);
                        close_key_wait_context(&ctx);
                        restore_auto_hud_if_needed(true);
                        return 0;
                    }
                    if (monitor.event_count > before_count) {
                        ++seen;
                    }
                    draw_screen_input_monitor_state(&monitor);
                    if (target > 0 && seen >= target) {
                        break;
                    }
                }

                if (rd < 0 && errno != EAGAIN && errno != EWOULDBLOCK) {
                    int saved_errno = errno;

                    a90_console_printf("inputmonitor: read: %s\r\n", strerror(saved_errno));
                    close_key_wait_context(&ctx);
                    restore_auto_hud_if_needed(true);
                    return -saved_errno;
                }
            }
            if ((fds[index].revents & (POLLERR | POLLHUP | POLLNVAL)) != 0) {
                a90_console_printf("inputmonitor: poll error revents=0x%x\r\n",
                        fds[index].revents);
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(true);
                return -EIO;
            }
        }
    }

    input_monitor_tick_state(&monitor, true);
    draw_screen_input_monitor_state(&monitor);
    close_key_wait_context(&ctx);
    restore_auto_hud_if_needed(true);
    return 0;
}

struct blind_menu_item {
    const char *name;
    const char *summary;
};

static void kms_draw_menu_section(struct kms_display_state *state,
                                  const struct screen_menu_page *page,
                                  size_t selected) {
    uint32_t scale = 5;
    uint32_t x = state->width / 24;
    uint32_t line_h = scale * 10;
    uint32_t card_h = line_h + scale * 4;
    uint32_t glyph_h = scale * 7;
    uint32_t slot = line_h + scale * 3;
    uint32_t card_w = state->width - x * 2;
    uint32_t menu_scale = scale;
    uint32_t y = state->height / 16;
    uint32_t status_bottom;
    uint32_t divider_y;
    uint32_t menu_y;
    uint32_t item_h = scale * 14;
    uint32_t item_gap = scale * 2;
    uint32_t log_tail_y;
    uint32_t page_scale;
    size_t i;

    if (y > glyph_h + glyph_h / 2 + scale * 2)
        y -= glyph_h + glyph_h / 2;

    status_bottom = y + 3 * slot + card_h;
    divider_y = status_bottom + scale * 5;
    menu_y = divider_y + scale * 17;

    kms_fill_rect(state, x, divider_y, card_w, 2, 0x383838);
    page_scale = shrink_text_scale(page->title, menu_scale, card_w / 2);
    kms_draw_text(state, x, divider_y + scale * 2,
                  page->title, 0xffcc33, page_scale);
    kms_draw_text(state, x, divider_y + scale * 10,
                  "VOL MOVE  PWR SELECT  COMBO BACK",
                  0x909090, menu_scale > 1 ? menu_scale - 1 : menu_scale);

    for (i = 0; i < page->count; ++i) {
        uint32_t iy = menu_y + (uint32_t)i * (item_h + item_gap);
        bool is_sel = (i == selected);
        uint32_t fill = is_sel ? 0x1a3560 : 0x141414;
        uint32_t name_color = is_sel ? 0xffffff : 0x707070;

        kms_fill_rect(state, x - scale, iy - scale, card_w, item_h, fill);
        if (is_sel)
            kms_fill_rect(state, x - scale, iy - scale, scale * 2, item_h, 0xffcc33);
        kms_draw_text(state, x + scale * 3, iy + (item_h - glyph_h) / 2,
                      page->items[i].name, name_color, menu_scale);
    }

    {
        uint32_t last_y = menu_y + (uint32_t)page->count * (item_h + item_gap);
        uint32_t summary_y = last_y + scale * 6;
        const char *summary = page->items[selected].summary;

        log_tail_y = summary_y;

        if (summary_y + glyph_h < state->height && summary != NULL && summary[0] != '\0') {
            kms_fill_rect(state, x, summary_y - scale, card_w, 1, 0x282828);
            kms_draw_text(state, x, summary_y + scale * 2,
                          summary, 0xffcc33,
                          shrink_text_scale(summary, menu_scale, card_w));
            log_tail_y = summary_y + glyph_h + scale * 8;
        }
    }

    kms_draw_log_tail_panel(state,
                            x,
                            log_tail_y,
                            card_w,
                            state->height - scale * 42,
                            16,
                            "LIVE LOG TAIL",
                            menu_scale > 3 ? menu_scale - 3 : menu_scale);
}

static int kms_read_log_tail(char lines[KMS_LOG_TAIL_MAX_LINES][KMS_LOG_TAIL_LINE_MAX],
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

static uint32_t kms_log_tail_line_color(const char *line) {
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

static void kms_log_tail_next_chunk(const char *line,
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

static int kms_log_tail_wrap_count(const char *line, size_t max_chars) {
    size_t offset = 0;
    int count = 0;

    if (max_chars == 0 || line[0] == '\0') {
        return 0;
    }
    while (line[offset] != '\0' && count < 16) {
        char chunk[KMS_LOG_TAIL_LINE_MAX];
        size_t next_offset;

        kms_log_tail_next_chunk(line,
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

static void kms_draw_log_tail_panel(struct kms_display_state *state,
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

    total = kms_read_log_tail(lines, max_lines);
    if (total <= 0) {
        return;
    }

    start = total;
    while (start > 0) {
        int rows = kms_log_tail_wrap_count(lines[start - 1], max_chars);

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

    kms_fill_rect(state, x - scale, y - scale, width, panel_h, 0x080808);
    kms_fill_rect(state, x, y, width - scale * 2, 1, 0x303030);
    kms_draw_text(state, x, y + scale * 2, title, 0xffcc33,
                  shrink_text_scale(title, scale, width - scale * 2));
    y += title_h + title_gap;

    visual_rows = 0;
    for (i = start; i < total && visual_rows < row_budget; ++i) {
        const char *line = lines[i];
        size_t offset = 0;
        uint32_t color = kms_log_tail_line_color(line);

        while (line[offset] != '\0' && visual_rows < row_budget) {
            char chunk[KMS_LOG_TAIL_LINE_MAX];
            size_t next_offset;
            uint32_t row_y = y + (uint32_t)visual_rows * (line_h + 2);

            kms_log_tail_next_chunk(line,
                                    offset,
                                    max_chars,
                                    chunk,
                                    sizeof(chunk),
                                    &next_offset);
            kms_draw_text(state, x, row_y, chunk, color, scale);
            offset = next_offset;
            ++visual_rows;
        }
    }
}

static void kms_draw_hud_log_tail(struct kms_display_state *state) {
    uint32_t scale = 3;
    uint32_t hud_scale = 5;
    uint32_t slot = (hud_scale * 10) + hud_scale * 3;
    uint32_t card_h = (hud_scale * 10) + hud_scale * 4;
    uint32_t glyph_h = hud_scale * 7;
    uint32_t x = state->width / 24;
    uint32_t card_w = state->width - x * 2;
    uint32_t y = state->height / 16;
    uint32_t area_y;

    if (y > glyph_h + glyph_h / 2 + hud_scale * 2)
        y -= glyph_h + glyph_h / 2;
    area_y = y + 3 * slot + card_h + hud_scale * 8;

    kms_draw_log_tail_panel(state,
                            x,
                            area_y,
                            card_w,
                            state->height - hud_scale * 16,
                            24,
                            "LOG TAIL",
                            scale);
}

static void print_blind_menu_selection(const struct blind_menu_item *items,
                                       size_t count,
                                       size_t selected) {
    a90_console_printf("blindmenu: [%d/%d] %s - %s\r\n",
            (int)(selected + 1),
            (int)count,
            items[selected].name,
            items[selected].summary);
}

static void print_screen_menu_selection(const struct screen_menu_page *page,
                                        size_t selected) {
    a90_console_printf("screenmenu: %s [%d/%d] %s - %s\r\n",
            page->title,
            (int)(selected + 1),
            (int)page->count,
            page->items[selected].name,
            page->items[selected].summary);
}

static uint32_t menu_text_scale(void) {
    if (kms_state.width >= 1080) {
        return 6;
    }
    if (kms_state.width >= 720) {
        return 4;
    }
    return 3;
}

static uint32_t about_text_scale(void) {
    if (kms_state.width >= 1080) {
        return 4;
    }
    if (kms_state.width >= 720) {
        return 3;
    }
    return 2;
}

static uint32_t shrink_text_scale(const char *text,
                                  uint32_t scale,
                                  uint32_t max_width) {
    while (scale > 1 && (uint32_t)strlen(text) * scale * 6 > max_width) {
        --scale;
    }
    return scale;
}

static int draw_screen_menu(const struct screen_menu_page *page,
                            size_t selected) {
    uint32_t scale;
    uint32_t title_scale;
    uint32_t footer_scale;
    uint32_t x;
    uint32_t y;
    uint32_t card_w;
    uint32_t item_h;
    uint32_t gap;
    uint32_t title_y;
    uint32_t list_y;
    uint32_t index;
    const char *footer = "VOL MOVE PWR SEL DBL/COMBO BACK";

    if (kms_begin_frame(0x050505) < 0) {
        return negative_errno_or(ENODEV);
    }

    scale = menu_text_scale();
    if (page->count > 15 && scale > 3) {
        scale = 3;
    } else if (page->count > 10 && scale > 4) {
        scale = 4;
    }
    title_scale = scale + 1;
    x = kms_state.width / 18;
    if (x < scale * 4) {
        x = scale * 4;
    }
    y = kms_state.height / 10;
    card_w = kms_state.width - (x * 2);
    item_h = scale * 17;
    gap = scale * 2;
    title_y = y;
    list_y = title_y + (title_scale * 9) + (scale * 5);

    kms_draw_text(&kms_state, x, title_y, page->title, 0xffcc33,
                  shrink_text_scale(page->title, title_scale, card_w));
    kms_draw_text(&kms_state, x, title_y + title_scale * 9,
                  "BUTTON ONLY CONTROL / BACK AT BOTTOM", 0xdddddd,
                  shrink_text_scale("BUTTON ONLY CONTROL / BACK AT BOTTOM", scale, card_w));

    for (index = 0; index < page->count; ++index) {
        uint32_t item_y = list_y + index * (item_h + gap);
        uint32_t fill = (index == selected) ? 0x204080 : 0x202020;
        uint32_t name_color = (index == selected) ? 0xffffff : 0xd0d0d0;
        uint32_t summary_color = (index == selected) ? 0xffcc33 : 0x909090;

        kms_fill_rect(&kms_state, x - scale, item_y - scale, card_w, item_h, fill);
        if (index == selected) {
            kms_fill_rect(&kms_state, x - scale, item_y - scale, scale * 2, item_h, 0xffcc33);
        }
        kms_draw_text(&kms_state, x + scale * 3, item_y + scale,
                      page->items[index].name, name_color, scale);
        kms_draw_text(&kms_state, x + scale * 3, item_y + scale * 9,
                      page->items[index].summary, summary_color, scale > 1 ? scale - 1 : scale);
    }

    footer_scale = shrink_text_scale(footer, scale, card_w);
    kms_draw_log_tail_panel(&kms_state,
                            x,
                            list_y + (uint32_t)page->count * (item_h + gap) + scale * 4,
                            card_w,
                            kms_state.height - footer_scale * 16,
                            12,
                            "LIVE LOG TAIL",
                            scale > 3 ? scale - 3 : (scale > 2 ? scale - 1 : scale));
    kms_draw_text(&kms_state, x, kms_state.height - footer_scale * 12,
                  footer, 0xffffff, footer_scale);

    if (kms_present_frame("screenmenu") < 0) {
        return negative_errno_or(EIO);
    }
    return 0;
}

static int draw_screen_log_summary(void) {
    char boot_summary[64];
    char line1[96];
    char line2[96];
    char line3[96];
    char line4[96];
    uint32_t scale;
    uint32_t x;
    uint32_t y;
    uint32_t card_w;
    uint32_t line_h;

    if (kms_begin_frame(0x050505) < 0) {
        return negative_errno_or(ENODEV);
    }

    a90_timeline_boot_summary(boot_summary, sizeof(boot_summary));
    snprintf(line1, sizeof(line1), "BOOT %.40s", boot_summary);
    snprintf(line2, sizeof(line2), "LOG %s", a90_log_ready() ? "READY" : "NOT READY");
    snprintf(line3, sizeof(line3), "LAST %.24s RC %d E %d",
             last_result.command,
             last_result.code,
             last_result.saved_errno);
    snprintf(line4, sizeof(line4), "PATH %.48s", a90_log_path());

    scale = menu_text_scale();
    x = kms_state.width / 18;
    if (x < scale * 4) {
        x = scale * 4;
    }
    y = kms_state.height / 8;
    card_w = kms_state.width - (x * 2);
    line_h = scale * 12;

    kms_draw_text(&kms_state, x, y, "A90 LOG SUMMARY", 0xffcc33, scale + 1);
    y += line_h + scale * 4;

    kms_fill_rect(&kms_state, x - scale, y - scale, card_w, line_h * 5, 0x202020);
    kms_draw_text(&kms_state, x, y, line1, 0xffffff,
                  shrink_text_scale(line1, scale, card_w - scale * 2));
    y += line_h;
    kms_draw_text(&kms_state, x, y, line2, 0xffffff,
                  shrink_text_scale(line2, scale, card_w - scale * 2));
    y += line_h;
    kms_draw_text(&kms_state, x, y, line3, 0xffffff,
                  shrink_text_scale(line3, scale, card_w - scale * 2));
    y += line_h;
    kms_draw_text(&kms_state, x, y, line4, 0xffffff,
                  shrink_text_scale(line4, scale, card_w - scale * 2));

    kms_draw_text(&kms_state, x, kms_state.height - scale * 12,
                  "PRESS ANY BUTTON TO RETURN", 0xffffff,
                  shrink_text_scale("PRESS ANY BUTTON TO RETURN", scale, card_w));

    if (kms_present_frame("screenlog") < 0) {
        return negative_errno_or(EIO);
    }
    return 0;
}

static const struct input_monitor_raw_entry *input_monitor_raw_entry_at(
        const struct input_monitor_state *monitor,
        size_t reverse_index) {
    size_t slot;

    if (reverse_index >= monitor->raw_count || monitor->raw_head == 0) {
        return NULL;
    }

    slot = (monitor->raw_head + INPUT_MONITOR_ROWS - 1 - reverse_index) %
           INPUT_MONITOR_ROWS;
    return &monitor->raw_entries[slot];
}

static uint32_t input_monitor_value_color(int value) {
    switch (value) {
    case 1:
        return 0x88ee88;
    case 0:
        return 0xffcc33;
    case 2:
        return 0x66ddff;
    default:
        return 0xff7777;
    }
}

static const char *input_monitor_gesture_class(enum input_gesture_id id) {
    switch (id) {
    case INPUT_GESTURE_VOLUP_CLICK:
    case INPUT_GESTURE_VOLDOWN_CLICK:
    case INPUT_GESTURE_POWER_CLICK:
        return "SINGLE CLICK";
    case INPUT_GESTURE_VOLUP_DOUBLE:
    case INPUT_GESTURE_VOLDOWN_DOUBLE:
    case INPUT_GESTURE_POWER_DOUBLE:
        return "DOUBLE CLICK";
    case INPUT_GESTURE_VOLUP_LONG:
    case INPUT_GESTURE_VOLDOWN_LONG:
    case INPUT_GESTURE_POWER_LONG:
        return "LONG HOLD";
    case INPUT_GESTURE_VOLUP_VOLDOWN:
    case INPUT_GESTURE_VOLUP_POWER:
    case INPUT_GESTURE_VOLDOWN_POWER:
    case INPUT_GESTURE_ALL_BUTTONS:
        return "COMBO INPUT";
    case INPUT_GESTURE_NONE:
        return "WAITING";
    default:
        return "UNKNOWN";
    }
}

static uint32_t input_monitor_gesture_color(enum input_gesture_id id) {
    switch (id) {
    case INPUT_GESTURE_VOLUP_CLICK:
    case INPUT_GESTURE_VOLDOWN_CLICK:
    case INPUT_GESTURE_POWER_CLICK:
        return 0x88ee88;
    case INPUT_GESTURE_VOLUP_DOUBLE:
    case INPUT_GESTURE_VOLDOWN_DOUBLE:
    case INPUT_GESTURE_POWER_DOUBLE:
        return 0xffcc33;
    case INPUT_GESTURE_VOLUP_LONG:
    case INPUT_GESTURE_VOLDOWN_LONG:
    case INPUT_GESTURE_POWER_LONG:
        return 0xff8844;
    case INPUT_GESTURE_VOLUP_VOLDOWN:
    case INPUT_GESTURE_VOLUP_POWER:
    case INPUT_GESTURE_VOLDOWN_POWER:
    case INPUT_GESTURE_ALL_BUTTONS:
        return 0x66ddff;
    case INPUT_GESTURE_NONE:
        return 0x808080;
    default:
        return 0xff7777;
    }
}

static uint32_t input_monitor_action_color(enum input_menu_action action) {
    switch (action) {
    case INPUT_MENU_ACTION_SELECT:
        return 0x88ee88;
    case INPUT_MENU_ACTION_BACK:
    case INPUT_MENU_ACTION_HIDE:
        return 0xffcc33;
    case INPUT_MENU_ACTION_PAGE_PREV:
    case INPUT_MENU_ACTION_PAGE_NEXT:
    case INPUT_MENU_ACTION_PREV:
    case INPUT_MENU_ACTION_NEXT:
        return 0x66ddff;
    case INPUT_MENU_ACTION_RESERVED:
        return 0xff7777;
    default:
        return 0xffffff;
    }
}

static int draw_screen_input_monitor_state(const struct input_monitor_state *monitor) {
    char summary[96];
    char timing[96];
    char buttons_line[96];
    char action_line[96];
    char metric_line[96];
    uint32_t scale;
    uint32_t title_scale;
    uint32_t big_scale;
    uint32_t left;
    uint32_t top;
    uint32_t content_width;
    uint32_t line_height;
    uint32_t row_gap;
    uint32_t row_height;
    uint32_t card_height;
    uint32_t panel_height;
    uint32_t panel_top;
    uint32_t panel_mid;
    uint32_t half_width;
    uint32_t class_color;
    uint32_t action_color;
    size_t index;

    if (kms_begin_frame(0x050505) < 0) {
        return negative_errno_or(ENODEV);
    }

    scale = about_text_scale();
    if (scale > 3) {
        scale = 3;
    }
    title_scale = scale + 1;
    big_scale = scale * 3;
    left = kms_state.width / 18;
    if (left < scale * 4) {
        left = scale * 4;
    }
    top = kms_state.height / 12;
    content_width = kms_state.width - (left * 2);
    line_height = scale * 10;
    row_gap = scale * 3;
    row_height = line_height * 2 + row_gap;
    panel_height = line_height * 9;
    card_height = panel_height + line_height +
                  (uint32_t)INPUT_MONITOR_ROWS * row_height +
                  scale * 4;

    snprintf(summary, sizeof(summary), "RAW %u  GESTURE %u",
             monitor->event_count,
             monitor->gesture_count);
    snprintf(timing, sizeof(timing), "DOWN/UP GAP HOLD / DBL %ld LONG %ld",
             INPUT_DOUBLE_CLICK_MS,
             INPUT_LONG_PRESS_MS);
    snprintf(buttons_line, sizeof(buttons_line), "BUTTONS  %s",
             monitor->gesture_mask);
    snprintf(action_line, sizeof(action_line), "ACTION   %s",
             input_menu_action_name(monitor->gesture_action));
    snprintf(metric_line, sizeof(metric_line),
             "click=%u  duration=%ldms  gap=%ldms",
             monitor->gesture_clicks,
             monitor->gesture_duration_ms,
             monitor->gesture_gap_ms);

    kms_draw_text(&kms_state, left, top, "TOOLS / INPUT MONITOR", 0xffcc33,
                  shrink_text_scale("TOOLS / INPUT MONITOR",
                                    title_scale,
                                    content_width));
    top += line_height;
    kms_draw_text(&kms_state, left, top, summary, 0x88ee88,
                  shrink_text_scale(summary, scale, content_width));
    top += line_height;
    kms_draw_text(&kms_state, left, top, timing, 0xdddddd,
                  shrink_text_scale(timing, scale, content_width));
    top += line_height + scale * 2;

    kms_fill_rect(&kms_state,
                  left - scale,
                  top - scale,
                  content_width,
                  card_height,
                  0x202020);

    panel_top = top;
    half_width = (content_width - scale * 4) / 2;
    class_color = input_monitor_gesture_color(monitor->gesture_id);
    action_color = input_monitor_action_color(monitor->gesture_action);

    kms_fill_rect(&kms_state,
                  left,
                  panel_top,
                  content_width - scale * 2,
                  panel_height,
                  0x101820);
    kms_fill_rect(&kms_state,
                  left,
                  panel_top,
                  scale * 3,
                  panel_height,
                  class_color);

    kms_draw_text(&kms_state,
                  left + scale * 5,
                  panel_top + scale * 4,
                  "DECODED INPUT LAYER",
                  0x909090,
                  scale);
    kms_draw_text(&kms_state,
                  left + scale * 5,
                  panel_top + line_height + scale * 4,
                  input_monitor_gesture_class(monitor->gesture_id),
                  class_color,
                  shrink_text_scale(input_monitor_gesture_class(monitor->gesture_id),
                                    big_scale,
                                    content_width - scale * 10));
    kms_draw_text(&kms_state,
                  left + scale * 5,
                  panel_top + line_height * 4,
                  monitor->gesture_title,
                  0xffffff,
                  shrink_text_scale(monitor->gesture_title,
                                    scale,
                                    content_width - scale * 10));

    panel_mid = panel_top + line_height * 5 + scale * 4;
    kms_fill_rect(&kms_state,
                  left + scale * 5,
                  panel_mid,
                  half_width - scale * 2,
                  line_height * 2,
                  0x182030);
    kms_fill_rect(&kms_state,
                  left + half_width + scale * 3,
                  panel_mid,
                  half_width - scale * 2,
                  line_height * 2,
                  0x182030);
    kms_draw_text(&kms_state,
                  left + scale * 7,
                  panel_mid + scale * 3,
                  buttons_line,
                  0x66ddff,
                  shrink_text_scale(buttons_line,
                                    scale,
                                    half_width - scale * 6));
    kms_draw_text(&kms_state,
                  left + half_width + scale * 5,
                  panel_mid + scale * 3,
                  action_line,
                  action_color,
                  shrink_text_scale(action_line,
                                    scale,
                                    half_width - scale * 6));
    kms_draw_text(&kms_state,
                  left + scale * 5,
                  panel_top + panel_height - line_height - scale * 3,
                  metric_line,
                  0xdddddd,
                  shrink_text_scale(metric_line,
                                    scale,
                                    content_width - scale * 10));

    top = panel_top + panel_height + line_height;

    for (index = 0; index < INPUT_MONITOR_ROWS; ++index) {
        const struct input_monitor_raw_entry *entry =
            input_monitor_raw_entry_at(monitor, index);
        uint32_t row_y = top + (uint32_t)index * row_height;
        uint32_t title_color;

        if (entry == NULL) {
            continue;
        }

        title_color = input_monitor_value_color(entry->value);
        kms_fill_rect(&kms_state,
                      left,
                      row_y - scale,
                      content_width - scale * 2,
                      line_height * 2 + scale,
                      index == 0 ? 0x283030 : 0x181818);
        kms_draw_text(&kms_state,
                      left + scale * 2,
                      row_y,
                      entry->title,
                      title_color,
                      shrink_text_scale(entry->title,
                                        scale,
                                        content_width - scale * 4));
        kms_draw_text(&kms_state,
                      left + scale * 5,
                      row_y + line_height,
                      entry->detail,
                      index == 0 ? 0xffffff : 0xa8a8a8,
                      shrink_text_scale(entry->detail,
                                        scale,
                                        content_width - scale * 7));
    }

    kms_draw_text(&kms_state,
                  left,
                  kms_state.height - scale * 12,
                  "ALL BUTTONS EXIT / BRIDGE hide",
                  0xffffff,
                  shrink_text_scale("ALL BUTTONS EXIT / BRIDGE hide",
                                    scale,
                                    content_width));

    if (kms_present_frame_verbose("inputmonitor", false) < 0) {
        return negative_errno_or(EIO);
    }
    return 0;
}

static int draw_screen_input_monitor_app(void) {
    return draw_screen_input_monitor_state(&auto_input_monitor);
}

static int draw_screen_info_page(const char *title,
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

    if (kms_begin_frame(0x050505) < 0) {
        return negative_errno_or(ENODEV);
    }

    lines[0] = line1;
    lines[1] = line2;
    lines[2] = line3;
    lines[3] = line4;

    scale = menu_text_scale();
    title_scale = scale + 1;
    x = kms_state.width / 18;
    if (x < scale * 4) {
        x = scale * 4;
    }
    y = kms_state.height / 8;
    card_w = kms_state.width - (x * 2);
    line_h = scale * 12;

    kms_draw_text(&kms_state, x, y, title, 0xffcc33,
                  shrink_text_scale(title, title_scale, card_w));
    y += line_h + scale * 4;

    kms_fill_rect(&kms_state, x - scale, y - scale, card_w, line_h * 5, 0x202020);
    for (index = 0; index < 4; ++index) {
        kms_draw_text(&kms_state, x, y + (uint32_t)index * line_h,
                      lines[index] != NULL ? lines[index] : "",
                      0xffffff,
                      shrink_text_scale(lines[index] != NULL ? lines[index] : "",
                                        scale, card_w - scale * 2));
    }

    kms_draw_text(&kms_state, x, kms_state.height - scale * 12,
                  footer, 0xffffff, shrink_text_scale(footer, scale, card_w));

    if (kms_present_frame("screeninfo") < 0) {
        return negative_errno_or(EIO);
    }
    return 0;
}

static int draw_screen_about_lines(const char *title,
                                   const char *const *lines,
                                   size_t count) {
    const char *footer = "PRESS ANY BUTTON TO RETURN";
    uint32_t scale;
    uint32_t title_scale;
    uint32_t left;
    uint32_t top;
    uint32_t content_width;
    uint32_t line_height;
    size_t index;

    if (kms_begin_frame(0x050505) < 0) {
        return negative_errno_or(ENODEV);
    }

    scale = about_text_scale();
    title_scale = scale + 1;
    left = kms_state.width / 18;
    if (left < scale * 4) {
        left = scale * 4;
    }
    top = kms_state.height / 12;
    content_width = kms_state.width - (left * 2);
    line_height = scale * 10;

    kms_draw_text(&kms_state, left, top, title, 0xffcc33,
                  shrink_text_scale(title, title_scale, content_width));
    top += line_height + scale * 4;

    kms_fill_rect(&kms_state,
                  left - scale,
                  top - scale,
                  content_width,
                  line_height * ((uint32_t)count + 1),
                  0x202020);

    for (index = 0; index < count; ++index) {
        const char *line = lines[index] != NULL ? lines[index] : "";
        uint32_t color = index == 0 ? 0x88ee88 : 0xffffff;

        kms_draw_text(&kms_state,
                      left,
                      top + (uint32_t)index * line_height,
                      line,
                      color,
                      shrink_text_scale(line, scale, content_width - scale * 2));
    }

    kms_draw_text(&kms_state,
                  left,
                  kms_state.height - scale * 12,
                  footer,
                  0xffffff,
                  shrink_text_scale(footer, scale, content_width));

    if (kms_present_frame("screenabout") < 0) {
        return negative_errno_or(EIO);
    }
    return 0;
}

static void kms_draw_rect_outline(struct kms_display_state *state,
                                  uint32_t x,
                                  uint32_t y,
                                  uint32_t width,
                                  uint32_t height,
                                  uint32_t thickness,
                                  uint32_t color) {
    if (thickness == 0) {
        thickness = 1;
    }
    if (width <= thickness * 2 || height <= thickness * 2) {
        kms_fill_rect(state, x, y, width, height, color);
        return;
    }
    kms_fill_rect(state, x, y, width, thickness, color);
    kms_fill_rect(state, x, y + height - thickness, width, thickness, color);
    kms_fill_rect(state, x, y, thickness, height, color);
    kms_fill_rect(state, x + width - thickness, y, thickness, height, color);
}

static int clamp_int_value(int value, int min_value, int max_value) {
    if (value < min_value) {
        return min_value;
    }
    if (value > max_value) {
        return max_value;
    }
    return value;
}

static const char *cutout_calibration_field_name(enum cutout_calibration_field field) {
    switch (field) {
    case CUTOUT_CAL_FIELD_X:
        return "X";
    case CUTOUT_CAL_FIELD_Y:
        return "Y";
    case CUTOUT_CAL_FIELD_SIZE:
        return "SIZE";
    default:
        return "?";
    }
}

static void cutout_calibration_clamp(struct cutout_calibration_state *cal) {
    int width = kms_state.width > 0 ? (int)kms_state.width : 1080;
    int height = kms_state.height > 0 ? (int)kms_state.height : 2400;
    int min_size = width / 40;
    int max_size = width / 8;
    int margin;

    if (min_size < 18) {
        min_size = 18;
    }
    if (max_size < min_size) {
        max_size = min_size;
    }
    cal->size = clamp_int_value(cal->size, min_size, max_size);
    margin = cal->size / 2 + 2;
    cal->center_x = clamp_int_value(cal->center_x, margin, width - margin);
    cal->center_y = clamp_int_value(cal->center_y, margin, height - margin);
    if ((int)cal->field < 0 || cal->field >= CUTOUT_CAL_FIELD_COUNT) {
        cal->field = CUTOUT_CAL_FIELD_Y;
    }
}

static void cutout_calibration_init(struct cutout_calibration_state *cal) {
    int width = kms_state.width > 0 ? (int)kms_state.width : 1080;
    int height = kms_state.height > 0 ? (int)kms_state.height : 2400;

    cal->center_x = width / 2;
    cal->center_y = height / 30;
    cal->size = width / 22;
    cal->field = CUTOUT_CAL_FIELD_Y;
    cutout_calibration_clamp(cal);
}

static void cutout_calibration_adjust(struct cutout_calibration_state *cal,
                                      int direction) {
    int step = 4;

    if (cal->field == CUTOUT_CAL_FIELD_SIZE) {
        step = 2;
    }
    switch (cal->field) {
    case CUTOUT_CAL_FIELD_X:
        cal->center_x += direction * step;
        break;
    case CUTOUT_CAL_FIELD_Y:
        cal->center_y += direction * step;
        break;
    case CUTOUT_CAL_FIELD_SIZE:
        cal->size += direction * step;
        break;
    default:
        break;
    }
    cutout_calibration_clamp(cal);
}

static bool cutout_calibration_feed_key(struct cutout_calibration_state *cal,
                                        const struct input_event *event,
                                        unsigned int *down_mask,
                                        long *power_down_ms,
                                        long *last_power_up_ms) {
    unsigned int mask;
    long now_ms;

    if (event->type != EV_KEY || event->value == 2) {
        return false;
    }

    mask = input_button_mask_from_key(event->code);
    if (mask == 0) {
        return false;
    }

    now_ms = monotonic_millis();
    if (event->value == 1) {
        *down_mask |= mask;
        if ((*down_mask & (INPUT_BUTTON_VOLUP | INPUT_BUTTON_VOLDOWN)) ==
            (INPUT_BUTTON_VOLUP | INPUT_BUTTON_VOLDOWN)) {
            return true;
        }
        if (event->code == KEY_VOLUMEUP) {
            cutout_calibration_adjust(cal, -1);
        } else if (event->code == KEY_VOLUMEDOWN) {
            cutout_calibration_adjust(cal, 1);
        } else if (event->code == KEY_POWER) {
            *power_down_ms = now_ms;
        }
        return false;
    }

    *down_mask &= ~mask;
    if (event->code == KEY_POWER) {
        long duration_ms = *power_down_ms > 0 ? now_ms - *power_down_ms : 0;

        *power_down_ms = 0;
        if (duration_ms >= INPUT_LONG_PRESS_MS) {
            return true;
        }
        if (*last_power_up_ms > 0 &&
            now_ms - *last_power_up_ms <= INPUT_DOUBLE_CLICK_MS) {
            *last_power_up_ms = 0;
            return true;
        }
        *last_power_up_ms = now_ms;
        cal->field = (enum cutout_calibration_field)
                     (((int)cal->field + 1) % CUTOUT_CAL_FIELD_COUNT);
    }
    return false;
}

static int draw_screen_cutout_calibration(const struct cutout_calibration_state *cal,
                                          bool interactive) {
    struct cutout_calibration_state local = *cal;
    char line[96];
    uint32_t scale;
    uint32_t small_scale;
    uint32_t width;
    uint32_t height;
    uint32_t center_x;
    uint32_t center_y;
    uint32_t size;
    uint32_t box_x;
    uint32_t box_y;
    uint32_t box_thick;
    uint32_t gap;
    uint32_t side_margin;
    uint32_t slot_y;
    uint32_t slot_h;
    uint32_t slot_label_y;
    uint32_t camera_zone_w;
    uint32_t camera_zone_x;
    uint32_t left_w;
    uint32_t right_x;
    uint32_t right_w;
    uint32_t safe_y;
    uint32_t safe_h;
    uint32_t panel_y;
    uint32_t panel_h;
    uint32_t panel_w;
    uint32_t footer_y;

    cutout_calibration_clamp(&local);
    if (kms_begin_frame(0x05070c) < 0) {
        return negative_errno_or(ENODEV);
    }

    scale = about_text_scale();
    if (scale < 2) {
        scale = 2;
    }
    small_scale = scale > 2 ? scale - 1 : scale;
    width = kms_state.width;
    height = kms_state.height;
    center_x = (uint32_t)local.center_x;
    center_y = (uint32_t)local.center_y;
    size = (uint32_t)local.size;
    box_x = center_x - size / 2;
    box_y = center_y - size / 2;
    box_thick = scale > 3 ? scale / 2 : 1;
    gap = scale * 3;
    side_margin = width / 24;
    if (side_margin < scale * 4) {
        side_margin = scale * 4;
    }
    footer_y = height > scale * 12 ? height - scale * 12 : height;

    slot_y = scale * 2;
    slot_h = center_y + size / 2 + scale * 12;
    if (slot_h < scale * 16) {
        slot_h = scale * 16;
    }
    slot_label_y = center_y + size / 2 + scale * 3;
    if (slot_label_y + scale * 8 > slot_y + slot_h) {
        slot_label_y = slot_y + scale * 2;
    }
    camera_zone_w = size + scale * 16;
    if (camera_zone_w < scale * 28) {
        camera_zone_w = scale * 28;
    }
    camera_zone_x = center_x > camera_zone_w / 2 ? center_x - camera_zone_w / 2 : 0;
    left_w = camera_zone_x > side_margin + gap ?
             camera_zone_x - side_margin - gap : 0;
    right_x = camera_zone_x + camera_zone_w + gap;
    right_w = side_margin + (width - side_margin * 2) > right_x ?
              side_margin + (width - side_margin * 2) - right_x : 0;

    if (left_w > scale * 18) {
        kms_fill_rect(&kms_state, side_margin, slot_y, left_w, slot_h, 0x07182a);
        kms_draw_rect_outline(&kms_state, side_margin, slot_y, left_w, slot_h,
                              box_thick, 0x315080);
        kms_draw_text_fit(&kms_state, side_margin + scale * 2,
                          slot_label_y,
                          "LEFT SAFE", 0x66ddff, small_scale,
                          left_w - scale * 4);
    }
    if (right_w > scale * 18) {
        kms_fill_rect(&kms_state, right_x, slot_y, right_w, slot_h, 0x07182a);
        kms_draw_rect_outline(&kms_state, right_x, slot_y, right_w, slot_h,
                              box_thick, 0x315080);
        kms_draw_text_fit(&kms_state, right_x + scale * 2,
                          slot_label_y,
                          "RIGHT SAFE", 0x66ddff, small_scale,
                          right_w - scale * 4);
    }
    kms_draw_rect_outline(&kms_state, camera_zone_x, slot_y,
                          camera_zone_w, slot_h, box_thick, 0xff8040);
    kms_draw_text_fit(&kms_state, camera_zone_x + scale * 2,
                      slot_label_y,
                      "CAMERA", 0xffcc33, small_scale,
                      camera_zone_w - scale * 4);

    kms_draw_rect_outline(&kms_state, box_x, box_y, size, size,
                          box_thick, 0xff8040);
    if (box_x > scale * 8) {
        kms_fill_rect(&kms_state, box_x - scale * 8, center_y,
                      scale * 8, box_thick, 0x66ddff);
    }
    if (box_x + size + scale * 8 < width) {
        kms_fill_rect(&kms_state, box_x + size, center_y,
                      scale * 8, box_thick, 0x66ddff);
    }
    if (box_y > scale * 8) {
        kms_fill_rect(&kms_state, center_x, box_y - scale * 8,
                      box_thick, scale * 8, 0x66ddff);
    }
    if (box_y + size + scale * 8 < height) {
        kms_fill_rect(&kms_state, center_x, box_y + size,
                      box_thick, scale * 8, 0x66ddff);
    }
    kms_fill_rect(&kms_state, center_x, center_y, box_thick, box_thick, 0xffffff);

    safe_y = center_y + size / 2 + scale * 12;
    if (safe_y < height / 5) {
        safe_y = height / 5;
    }
    if (safe_y + scale * 32 < footer_y) {
        safe_h = footer_y - safe_y - scale * 4;
        kms_draw_rect_outline(&kms_state,
                              side_margin,
                              safe_y,
                              width - side_margin * 2,
                              safe_h,
                              box_thick,
                              0x4060a0);
        kms_fill_rect(&kms_state, width / 2, safe_y,
                      box_thick, safe_h, 0x604020);
        kms_fill_rect(&kms_state, side_margin,
                      safe_y + safe_h / 2,
                      width - side_margin * 2,
                      box_thick,
                      0x604020);
    }

    panel_y = safe_y + scale * 4;
    panel_w = width - side_margin * 2;
    panel_h = scale * 42;
    if (panel_y + panel_h > footer_y) {
        panel_y = height / 3;
    }
    kms_fill_rect(&kms_state, side_margin, panel_y,
                  panel_w, panel_h, 0x101820);
    kms_draw_rect_outline(&kms_state, side_margin, panel_y,
                          panel_w, panel_h, box_thick, 0x315080);
    kms_draw_text_fit(&kms_state, side_margin + scale * 2,
                      panel_y + scale * 2,
                      interactive ? "ALIGN ORANGE BOX TO CAMERA HOLE"
                                  : "REFERENCE: ORANGE BOX SHOULD MATCH CAMERA",
                      0x88ee88, small_scale, panel_w - scale * 4);
    snprintf(line, sizeof(line), "X=%d  Y=%d  SIZE=%d  FIELD=%s",
             local.center_x,
             local.center_y,
             local.size,
             cutout_calibration_field_name(local.field));
    kms_draw_text_fit(&kms_state, side_margin + scale * 2,
                      panel_y + scale * 12,
                      line, 0xffffff, small_scale,
                      panel_w - scale * 4);
    kms_draw_text_fit(&kms_state, side_margin + scale * 2,
                      panel_y + scale * 22,
                      interactive ? "VOL+/- ADJUST  POWER NEXT FIELD"
                                  : "SHELL: cutoutcal [x y size]",
                      0xffcc33, small_scale, panel_w - scale * 4);
    kms_draw_text_fit(&kms_state, side_margin + scale * 2,
                      panel_y + scale * 32,
                      interactive ? "PWR LONG/DBL OR VOL+DN BACK"
                                  : "MENU APP: TOOLS > CUTOUT CAL",
                      0xdddddd, small_scale, panel_w - scale * 4);
    kms_draw_text_fit(&kms_state, side_margin, footer_y,
                      interactive ? "CALIBRATION MODE" : "DISPLAYTEST SAFE",
                      0xffffff, small_scale, width - side_margin * 2);

    if (kms_present_frame("cutoutcal") < 0) {
        return negative_errno_or(EIO);
    }
    return 0;
}

static const char *display_test_page_title(unsigned int page_index) {
    switch (page_index % DISPLAY_TEST_PAGE_COUNT) {
    case 0:
        return "COLOR / PIXEL";
    case 1:
        return "FONT / WRAP";
    case 2:
        return "SAFE / CUTOUT";
    case 3:
        return "HUD / MENU";
    default:
        return "DISPLAY";
    }
}

static int draw_screen_display_test_page(unsigned int page_index) {
    struct display_test_color {
        const char *name;
        uint32_t fill;
        uint32_t text;
    };
    static const struct display_test_color palette[] = {
        { "BLACK",  0x000000, 0xffffff },
        { "WHITE",  0xffffff, 0x000000 },
        { "RED",    0xd84040, 0xffffff },
        { "GREEN",  0x30d060, 0x000000 },
        { "BLUE",   0x3080ff, 0xffffff },
        { "YELLOW", 0xffcc33, 0x000000 },
        { "CYAN",   0x40d8ff, 0x000000 },
        { "GRAY",   0x606060, 0xffffff },
    };
    static const char *layout_items[] = {
        "HIDE MENU",
        "STATUS",
        "LOG",
        "TOOLS",
        "POWER",
    };
    const char *wrap_sample =
        "LONG LOG LINE WRAPS INTO SAFE WIDTH WITHOUT CLIPPING AND KEEPS WORD BOUNDARIES";
    char line[96];
    char chunk[96];
    const char *cursor;
    uint32_t scale;
    uint32_t small_scale;
    uint32_t title_scale;
    uint32_t left;
    uint32_t top;
    uint32_t body_top;
    uint32_t content_width;
    uint32_t line_height;
    uint32_t gap;
    uint32_t swatch_width;
    uint32_t swatch_height;
    uint32_t footer_y;
    uint32_t max_chars;
    size_t wrap_offset;
    size_t index;

    page_index %= DISPLAY_TEST_PAGE_COUNT;
    if (page_index == 2) {
        struct cutout_calibration_state cal;

        cutout_calibration_init(&cal);
        return draw_screen_cutout_calibration(&cal, false);
    }

    if (kms_begin_frame(0x05070c) < 0) {
        return negative_errno_or(ENODEV);
    }

    scale = about_text_scale();
    if (scale < 2) {
        scale = 2;
    }
    small_scale = scale > 2 ? scale - 1 : scale;
    title_scale = scale + 1;
    left = kms_state.width / 24;
    if (left < scale * 4) {
        left = scale * 4;
    }
    top = kms_state.height / 16;
    content_width = kms_state.width > left * 2 ? kms_state.width - (left * 2) : kms_state.width;
    line_height = scale * 10;
    gap = scale * 3;
    footer_y = kms_state.height > scale * 14 ? kms_state.height - scale * 14 : kms_state.height;

    kms_draw_rect_outline(&kms_state, left - scale, top - scale,
                          content_width + scale * 2,
                          footer_y - top + scale,
                          scale,
                          0x315080);

    snprintf(line, sizeof(line), "TOOLS / DISPLAY TEST %u/%u",
             page_index + 1,
             DISPLAY_TEST_PAGE_COUNT);
    kms_draw_text_fit(&kms_state, left, top, line,
                      0xffcc33, title_scale, content_width);
    top += line_height + gap;
    kms_draw_text_fit(&kms_state, left, top, display_test_page_title(page_index),
                      0x88aaff, scale, content_width);
    top += line_height + gap;
    body_top = top;

    if (page_index == 0) {
        swatch_width = (content_width - gap) / 2;
        swatch_height = line_height * 2;
        for (index = 0; index < SCREEN_MENU_COUNT(palette); ++index) {
            uint32_t col = (uint32_t)(index % 2);
            uint32_t row = (uint32_t)(index / 2);
            uint32_t swatch_x = left + col * (swatch_width + gap);
            uint32_t swatch_y = body_top + row * (swatch_height + gap);

            kms_fill_rect(&kms_state, swatch_x, swatch_y,
                          swatch_width, swatch_height, palette[index].fill);
            kms_fill_rect(&kms_state, swatch_x, swatch_y,
                          swatch_width, scale, 0xffffff);
            kms_draw_text_fit(&kms_state,
                              swatch_x + scale * 2,
                              swatch_y + scale * 5,
                              palette[index].name,
                              palette[index].text,
                              scale,
                              swatch_width - scale * 4);
        }
        top = body_top + ((uint32_t)(SCREEN_MENU_COUNT(palette) + 1) / 2) *
              (swatch_height + gap) + gap;
        kms_draw_text_fit(&kms_state, left, top,
                          "PIXEL FORMAT XBGR8888 / RGB LABEL CHECK",
                          0x88ee88, small_scale, content_width);
        top += line_height;
        kms_draw_text_fit(&kms_state, left, top,
                          "WHITE BAR SHOULD BE WHITE, RED/GREEN/BLUE SHOULD MATCH LABELS",
                          0xdddddd, small_scale, content_width);
    } else if (page_index == 1) {
        for (index = 1; index <= 8; ++index) {
            uint32_t row_scale = (uint32_t)index;
            uint32_t row_height = row_scale * 8 + scale * 2;

            if (top + row_height >= footer_y - line_height * 5) {
                break;
            }
            snprintf(line, sizeof(line), "SCALE %u ABC123 0.8.15", row_scale);
            kms_fill_rect(&kms_state, left, top,
                          content_width, row_height,
                          index % 2 ? 0x101620 : 0x182030);
            kms_draw_text_fit(&kms_state, left + scale * 2, top + scale,
                              line, 0xffffff, row_scale,
                              content_width - scale * 4);
            top += row_height + scale;
        }
        top += gap;
        kms_draw_text_fit(&kms_state, left, top, "WRAP SAMPLE",
                          0x88aaff, scale, content_width);
        top += line_height;
        cursor = wrap_sample;
        max_chars = content_width / (small_scale * 6);
        if (max_chars < 8) {
            max_chars = 8;
        }
        wrap_offset = 0;
        for (index = 0; cursor[wrap_offset] != '\0' && index < 5; ++index) {
            size_t next_offset;

            kms_log_tail_next_chunk(cursor,
                                    wrap_offset,
                                    max_chars,
                                    chunk,
                                    sizeof(chunk),
                                    &next_offset);
            kms_draw_text_fit(&kms_state, left + scale * 2, top,
                              chunk, 0xffffff, small_scale,
                              content_width - scale * 4);
            top += small_scale * 10;
            wrap_offset = next_offset;
        }
    } else if (page_index == 2) {
        uint32_t cutout_y = body_top + gap;
        uint32_t cutout_h = line_height * 3;
        uint32_t cutout_w = content_width / 5;
        uint32_t cutout_x;
        uint32_t cutout_center_x = kms_state.width / 2;
        uint32_t cutout_center_y = cutout_y + cutout_h / 2;
        uint32_t pocket_w;
        uint32_t right_x;
        uint32_t right_w;
        uint32_t hole = scale * 10;
        uint32_t grid_y;
        uint32_t grid_h;
        uint32_t center_x;
        uint32_t center_y;
        uint32_t label_y;
        uint32_t legend_y;
        uint32_t chip;

        if (cutout_w < scale * 24) {
            cutout_w = scale * 24;
        }
        if (cutout_w > content_width / 3) {
            cutout_w = content_width / 3;
        }
        cutout_x = (kms_state.width - cutout_w) / 2;
        pocket_w = cutout_x > left + gap ? cutout_x - left - gap : 0;
        right_x = cutout_x + cutout_w + gap;
        right_w = left + content_width > right_x ? left + content_width - right_x : 0;

        if (pocket_w > scale * 16) {
            kms_fill_rect(&kms_state, left, cutout_y, pocket_w, cutout_h, 0x07182a);
            kms_draw_rect_outline(&kms_state, left, cutout_y, pocket_w, cutout_h,
                                  scale, 0x315080);
            kms_draw_text_fit(&kms_state, left + scale * 2, cutout_y + scale * 2,
                              "LEFT SAFE", 0x66ddff, small_scale,
                              pocket_w - scale * 4);
        }
        kms_fill_rect(&kms_state, cutout_x, cutout_y, cutout_w, cutout_h, 0x281018);
        kms_draw_rect_outline(&kms_state, cutout_x, cutout_y, cutout_w, cutout_h,
                              scale, 0xff8040);
        kms_draw_text_fit(&kms_state, cutout_x + scale * 2, cutout_y + scale * 2,
                          "CAMERA", 0xffcc33, small_scale,
                          cutout_w - scale * 4);
        if (hole > cutout_h - scale * 2) {
            hole = cutout_h - scale * 2;
        }
        if (hole >= scale * 4) {
            kms_fill_rect(&kms_state,
                          cutout_center_x - hole / 2,
                          cutout_center_y - hole / 2,
                          hole,
                          hole,
                          0x000000);
            kms_draw_rect_outline(&kms_state,
                                  cutout_center_x - hole / 2,
                                  cutout_center_y - hole / 2,
                                  hole,
                                  hole,
                                  scale,
                                  0xffffff);
        }
        if (right_w > scale * 16) {
            kms_fill_rect(&kms_state, right_x, cutout_y, right_w, cutout_h, 0x07182a);
            kms_draw_rect_outline(&kms_state, right_x, cutout_y, right_w, cutout_h,
                                  scale, 0x315080);
            kms_draw_text_fit(&kms_state, right_x + scale * 2, cutout_y + scale * 2,
                              "RIGHT SAFE", 0x66ddff, small_scale,
                              right_w - scale * 4);
        }

        grid_y = cutout_y + cutout_h + gap * 3;
        grid_h = footer_y > grid_y + line_height ? footer_y - grid_y - line_height : 0;
        if (grid_h >= line_height * 4) {
            center_x = left + content_width / 2;
            center_y = grid_y + grid_h / 2;
            label_y = grid_y + scale * 2;
            kms_fill_rect(&kms_state, left, grid_y, content_width, grid_h, 0x0b1018);
            kms_draw_rect_outline(&kms_state, left, grid_y, content_width, grid_h,
                                  scale, 0xff8040);
            kms_fill_rect(&kms_state, center_x, grid_y, scale, grid_h, 0x604020);
            kms_fill_rect(&kms_state, left, center_y, content_width, scale, 0x604020);
            kms_draw_rect_outline(&kms_state,
                                  left + content_width / 10,
                                  grid_y + grid_h / 7,
                                  content_width * 4 / 5,
                                  grid_h * 5 / 7,
                                  scale,
                                  0x4060a0);
            kms_fill_rect(&kms_state, left + scale, label_y,
                          content_width - scale * 2,
                          line_height * 2 + scale,
                          0x101820);
            kms_draw_text_fit(&kms_state, left + scale * 3, label_y + scale,
                              "SAFE GRID", 0x88ee88, small_scale,
                              content_width - scale * 6);
            kms_draw_text_fit(&kms_state, left + scale * 3,
                              label_y + line_height,
                              "ORANGE EDGE  BLUE CONTENT", 0xdddddd,
                              small_scale, content_width - scale * 6);
            chip = scale * 4;
            legend_y = grid_y + grid_h;
            if (legend_y > line_height * 2 + scale * 6) {
                legend_y -= line_height * 2 + scale * 6;
            }
            if (legend_y > label_y + line_height * 3 && content_width > scale * 28) {
                kms_fill_rect(&kms_state, left + scale * 3, legend_y,
                              chip, chip, 0xff8040);
                kms_draw_text_fit(&kms_state, left + scale * 9,
                                  legend_y - scale,
                                  "EDGE", 0xffcc33, small_scale,
                                  content_width / 3);
                kms_fill_rect(&kms_state, left + content_width / 2,
                              legend_y, chip, chip, 0x4060a0);
                kms_draw_text_fit(&kms_state,
                                  left + content_width / 2 + scale * 6,
                                  legend_y - scale,
                                  "CONTENT", 0x66ddff, small_scale,
                                  content_width / 3);
            }
        }
    } else {
        uint32_t card_y = body_top;
        uint32_t card_h = line_height * 3;
        uint32_t half_w = (content_width - gap) / 2;

        kms_draw_status_overlay(&kms_state, left, card_y);
        card_y += line_height * 5;
        kms_draw_text_fit(&kms_state, left, card_y,
                          "HUD/MENU PREVIEW - CHECK SPACING AND TEXT WEIGHT",
                          0x88ee88, small_scale, content_width);
        card_y += line_height + gap;
        for (index = 0; index < SCREEN_MENU_COUNT(layout_items); ++index) {
            uint32_t col = (uint32_t)(index % 2);
            uint32_t row = (uint32_t)(index / 2);
            uint32_t item_x = left + col * (half_w + gap);
            uint32_t item_y = card_y + row * (card_h + gap);
            uint32_t fill = index == 0 ? 0xd84040 : 0x182030;
            uint32_t edge = index == 0 ? 0x66ddff : 0x315080;

            if (item_y + card_h >= footer_y - line_height) {
                break;
            }
            kms_fill_rect(&kms_state, item_x, item_y, half_w, card_h, fill);
            kms_draw_rect_outline(&kms_state, item_x, item_y, half_w, card_h,
                                  scale, edge);
            kms_draw_text_fit(&kms_state,
                              item_x + scale * 2,
                              item_y + scale * 4,
                              layout_items[index],
                              0xffffff,
                              scale,
                              half_w - scale * 4);
        }
        kms_draw_text_fit(&kms_state,
                          left,
                          footer_y - line_height * 2,
                          "PREVIEW ONLY: REAL MENU STILL USES LIVE STATUS + LOG TAIL",
                          0xdddddd,
                          small_scale,
                          content_width - scale * 4);
    }

    kms_draw_text_fit(&kms_state, left, footer_y, "VOL+/- PAGE  POWER BACK",
                      0xffffff, small_scale, content_width);

    if (kms_present_frame("displaytest") < 0) {
        return negative_errno_or(EIO);
    }
    return 0;
}

static int draw_screen_display_test(void) {
    return draw_screen_display_test_page(0);
}

static int draw_screen_about_version(void) {
    char version_line[96];
    const char *lines[5];

    snprintf(version_line, sizeof(version_line), "VERSION %s (%s)", INIT_VERSION, INIT_BUILD);
    lines[0] = INIT_BANNER;
    lines[1] = version_line;
    lines[2] = INIT_CREATOR;
    lines[3] = "KERNEL STOCK ANDROID LINUX 4.14";
    lines[4] = "RUNTIME CUSTOM STATIC PID 1";

    return draw_screen_about_lines("ABOUT / VERSION", lines, SCREEN_MENU_COUNT(lines));
}

static int draw_screen_about_changelog(void) {
    const char *lines[] = {
        "0.8.15 v84 CMDPROTO API",
        "0.8.14 v83 CONSOLE API",
        "0.8.13 v82 LOG TIMELINE API",
        "0.8.12 v81 CONFIG UTIL API",
        "0.8.11 v80 SOURCE MODULES",
        "0.8.10 v79 BOOT SD PROBE",
        "0.8.9 v78 SD WORKSPACE",
        "0.8.8 v77 DISPLAY TEST PAGES",
        "0.8.7 v76 AT FRAGMENT FILTER",
        "0.8.6 v75 QUIET IDLE REATTACH",
        "0.8.5 v74 CMDV1 ARG ENCODING",
        "0.8.4 v73 CMDV1 PROTOCOL",
        "0.8.3 v72 DISPLAY TEST FIX",
        "0.8.2 v71 MENU LOG TAIL",
        "0.8.1 v70 INPUT MONITOR APP",
        "0.8.0 v69 INPUT GESTURE LAYOUT",
        "0.7.5 v68 LOG TAIL + MORE HISTORY",
        "0.7.4 v67 DETAIL CHANGELOG UI",
        "0.7.3 v66 ABOUT + VERSIONING",
        "0.7.2 v65 SPLASH SAFE LAYOUT",
        "0.7.1 v64 CUSTOM BOOT SPLASH",
        "0.7.0 v63 APP MENU + CPU STRESS",
        "0.6.0 v62 CPU STRESS / DEV NODES",
        "0.5.1 v61 CPU/GPU USAGE HUD",
        "0.5.0 v60 NETSERVICE / RECONNECT",
        "0.4.1 v59 AT SERIAL FILTER",
        "0.4.0 v55 NCM TCP CONTROL",
        "0.3.0 v53 MENU BUSY GATE",
        "0.2.0 v40 SHELL LOG HUD CORE",
        "0.1.0 v1  NATIVE INIT ORIGIN",
    };

    return draw_screen_about_lines("ABOUT / CHANGELOG", lines, SCREEN_MENU_COUNT(lines));
}

static int draw_screen_changelog_v0815(void) {
    const char *lines[] = {
        "0.8.15 v84 CMDPROTO API",
        "Adds shared a90_cmdproto.c/h",
        "Moves A90P1 frame helpers",
        "Moves cmdv1x argv decoder",
        "Keeps shell dispatch unchanged",
        "Preserves host protocol output",
    };

    return draw_screen_about_lines("CHANGELOG / 0.8.15", lines, SCREEN_MENU_COUNT(lines));
}

static int draw_screen_changelog_v0814(void) {
    const char *lines[] = {
        "0.8.14 v83 CONSOLE API",
        "Adds shared a90_console.c/h",
        "Moves console fd state out",
        "Moves attach/reattach API",
        "Moves readline/cancel polling",
        "Keeps cmdv1/shell unchanged",
        "Prepares cmdproto boundary work",
    };

    return draw_screen_about_lines("CHANGELOG / 0.8.14", lines, SCREEN_MENU_COUNT(lines));
}

static int draw_screen_changelog_v0813(void) {
    const char *lines[] = {
        "0.8.13 v82 LOG TIMELINE API",
        "Adds shared a90_log.c/h",
        "Adds shared a90_timeline.c/h",
        "Moves log path state out",
        "Moves timeline ring state out",
        "Keeps console/shell stable",
        "Prepares console boundary work",
    };

    return draw_screen_about_lines("CHANGELOG / 0.8.13", lines, SCREEN_MENU_COUNT(lines));
}

static int draw_screen_changelog_v0812(void) {
    const char *lines[] = {
        "0.8.12 v81 CONFIG UTIL API",
        "Adds shared a90_config.h",
        "Adds shared a90_util.c/h",
        "Moves common file helpers",
        "Moves time/errno helpers",
        "Keeps PID1 behavior stable",
    };

    return draw_screen_about_lines("CHANGELOG / 0.8.12", lines, SCREEN_MENU_COUNT(lines));
}

static int draw_screen_changelog_v0811(void) {
    const char *lines[] = {
        "0.8.11 v80 SOURCE MODULES",
        "Splits PID1 source by module",
        "Keeps one static /init binary",
        "Preserves v79 runtime behavior",
        "Groups core/display/input/menu",
        "Groups storage/network/shell",
        "Prepares future helper split",
    };

    return draw_screen_about_lines("CHANGELOG / 0.8.11", lines, SCREEN_MENU_COUNT(lines));
}

static int draw_screen_changelog_v0810(void) {
    const char *lines[] = {
        "0.8.10 v79 BOOT SD PROBE",
        "Checks SD during boot",
        "Verifies expected ext4 UUID",
        "Mounts /mnt/sdext/a90 if OK",
        "Runs boot-time rw probe",
        "Shows splash probe progress",
        "Warns HUD on SD fallback",
        "Keeps /cache fallback safe",
        "Adds storage status command",
    };

    return draw_screen_about_lines("CHANGELOG / 0.8.10", lines, SCREEN_MENU_COUNT(lines));
}

static int draw_screen_changelog_v089(void) {
    const char *lines[] = {
        "0.8.9 v78 SD WORKSPACE",
        "Added mountsd command",
        "Controls ext4 SD at /mnt/sdext",
        "Creates /mnt/sdext/a90 workspace",
        "Adds bin logs tmp rootfs images",
        "Supports ro rw off init status",
        "Status shows mount and free MB",
        "Keeps UFS for boot and rescue",
        "Moves experiments toward SD",
    };

    return draw_screen_about_lines("CHANGELOG / 0.8.9", lines, SCREEN_MENU_COUNT(lines));
}

static int draw_screen_changelog_v088(void) {
    const char *lines[] = {
        "0.8.8 v77 DISPLAY TEST PAGES",
        "Split display test into pages",
        "Page 1 color and pixel format",
        "Page 2 font scale and wrap",
        "Page 3 safe/cutout reference",
        "Page 4 HUD/menu preview",
        "Added cutoutcal command/app",
        "VOL adjusts POWER changes field",
        "VOL up/down changes page",
        "displaytest [page] via shell",
    };

    return draw_screen_about_lines("CHANGELOG / 0.8.8", lines, SCREEN_MENU_COUNT(lines));
}

static int draw_screen_changelog_v087(void) {
    const char *lines[] = {
        "0.8.7 v76 AT FRAGMENT FILTER",
        "Ignores short A/T fragments",
        "Covers A T AT ATA ATAT",
        "Keeps full AT probe filter",
        "Prevents unknown command spam",
        "Logs ignored fragment category",
        "Normal lowercase shell remains",
        "Keeps cmdv1/cmdv1x unchanged",
    };

    return draw_screen_about_lines("CHANGELOG / 0.8.7", lines, SCREEN_MENU_COUNT(lines));
}

static int draw_screen_changelog_v086(void) {
    const char *lines[] = {
        "0.8.6 v75 QUIET IDLE REATTACH",
        "Idle serial reattach still active",
        "Interval increased to 60 seconds",
        "Success logs hidden for idle path",
        "Failures remain visible in log tail",
        "Manual reattach logs still visible",
        "Keeps recovery behavior unchanged",
        "Reduces live log tail noise",
    };

    return draw_screen_about_lines("CHANGELOG / 0.8.6", lines, SCREEN_MENU_COUNT(lines));
}

static int draw_screen_changelog_v085(void) {
    const char *lines[] = {
        "0.8.5 v74 CMDV1 ARG ENCODING",
        "Added cmdv1x len:hex argv",
        "Keeps old cmdv1 token path",
        "Host a90ctl auto-selects format",
        "Whitespace args stay framed",
        "Special chars avoid raw fallback",
        "Decoder validates length and hex",
        "Prepared safer automation calls",
    };

    return draw_screen_about_lines("CHANGELOG / 0.8.5", lines, SCREEN_MENU_COUNT(lines));
}

static int draw_screen_changelog_v084(void) {
    const char *lines[] = {
        "0.8.4 v73 CMDV1 PROTOCOL",
        "Added cmdv1 command wrapper",
        "Emits A90P1 BEGIN and END",
        "Reports rc errno duration flags",
        "Keeps normal shell output intact",
        "Unknown/busy states are framed",
        "Host a90ctl can parse results",
        "Bridge automation gets safer",
    };

    return draw_screen_about_lines("CHANGELOG / 0.8.4", lines, SCREEN_MENU_COUNT(lines));
}

static int draw_screen_changelog_v083(void) {
    const char *lines[] = {
        "0.8.3 v72 DISPLAY TEST FIX",
        "Added TOOLS / DISPLAY TEST",
        "Added color/font/wrap grid screen",
        "Added cutout top slot guide",
        "Widened main safe-area grid",
        "Fixed XBGR8888 color packing",
        "Displaytest command draws directly",
        "Validated flash and framebuffer",
    };

    return draw_screen_about_lines("CHANGELOG / 0.8.3", lines, SCREEN_MENU_COUNT(lines));
}

static int draw_screen_changelog_v082(void) {
    const char *lines[] = {
        "0.8.2 v71 MENU LOG TAIL",
        "Shared log tail panel renderer",
        "HUD hidden keeps log tail view",
        "HUD menu also shows live log tail",
        "screenmenu uses spare space too",
        "Log colors highlight failures/input",
        "Long log lines wrap on screen",
        "Busy gate allows safe commands",
    };

    return draw_screen_about_lines("CHANGELOG / 0.8.2", lines, SCREEN_MENU_COUNT(lines));
}

static int draw_screen_changelog_v081(void) {
    const char *lines[] = {
        "0.8.1 v70 INPUT MONITOR APP",
        "Added TOOLS / INPUT MONITOR",
        "Shows raw DOWN/UP/REPEAT events",
        "Shows gap between input events",
        "Shows key hold duration on release",
        "Shows decoded gesture/action",
        "Added inputmonitor shell command",
        "All-buttons exits monitor app",
    };

    return draw_screen_about_lines("CHANGELOG / 0.8.1", lines, SCREEN_MENU_COUNT(lines));
}

static int draw_screen_changelog_v080(void) {
    const char *lines[] = {
        "0.8.0 v69 INPUT GESTURE LAYOUT",
        "Added inputlayout command",
        "Added waitgesture debug command",
        "Single click keeps old controls",
        "Double/long volume page moves",
        "POWER double and VOL combo back",
        "POWER long reserved for safety",
        "screenmenu/blindmenu use gestures",
    };

    return draw_screen_about_lines("CHANGELOG / 0.8.0", lines, SCREEN_MENU_COUNT(lines));
}

static int draw_screen_changelog_v075(void) {
    const char *lines[] = {
        "0.7.5 v68 LOG TAIL + HISTORY",
        "HUD menu hidden: log tail display",
        "HUD menu visible: item summary shown",
        "Changelog: 14 versions from v1",
        "Added v68 v61 v59 v55 v53 v40 v1",
        "Detail screens for all versions",
        "Log reads /cache/native-init.log",
        "Tail shows last 14 lines",
    };

    return draw_screen_about_lines("CHANGELOG / 0.7.5", lines, SCREEN_MENU_COUNT(lines));
}

static int draw_screen_changelog_v074(void) {
    const char *lines[] = {
        "0.7.4 v67 DETAIL CHANGELOG UI",
        "ABOUT text scale reduced",
        "VERSION/CREDITS use compact text",
        "CHANGELOG opens version list",
        "Each version opens detail screen",
        "Longer notes fit vertical display",
        "Current build remains visible",
        "Footer kept press-any-button",
    };

    return draw_screen_about_lines("CHANGELOG / 0.7.4", lines, SCREEN_MENU_COUNT(lines));
}

static int draw_screen_changelog_v073(void) {
    const char *lines[] = {
        "0.7.3 v66 ABOUT + VERSIONING",
        "Added semantic version display",
        "Added made by temmie0214",
        "Added APPS / ABOUT folder",
        "Added VERSION screen",
        "Added CHANGELOG summary screen",
        "Added CREDITS screen",
        "Updated version command output",
        "Updated status creator output",
        "Added VERSIONING.md and CHANGELOG.md",
    };

    return draw_screen_about_lines("CHANGELOG / 0.7.3", lines, SCREEN_MENU_COUNT(lines));
}

static int draw_screen_changelog_v072(void) {
    const char *lines[] = {
        "0.7.2 v65 SPLASH SAFE LAYOUT",
        "Reduced boot splash text scale",
        "Widened safe screen margins",
        "Shortened status rows",
        "Moved footer into safe area",
        "Avoided punch-hole overlap",
        "Verified visible splash layout",
        "Kept auto HUD transition",
    };

    return draw_screen_about_lines("CHANGELOG / 0.7.2", lines, SCREEN_MENU_COUNT(lines));
}

static int draw_screen_changelog_v071(void) {
    const char *lines[] = {
        "0.7.1 v64 CUSTOM BOOT SPLASH",
        "Replaced TEST boot screen",
        "Added A90 NATIVE INIT splash",
        "Added boot summary text",
        "Recorded display-splash timeline",
        "Kept shell handoff stable",
        "Kept status HUD after boot",
    };

    return draw_screen_about_lines("CHANGELOG / 0.7.1", lines, SCREEN_MENU_COUNT(lines));
}

static int draw_screen_changelog_v070(void) {
    const char *lines[] = {
        "0.7.0 v63 APP MENU",
        "Added APPS hierarchy",
        "Added MONITORING folder",
        "Added TOOLS folder",
        "Added LOGS folder",
        "Added CPU STRESS duration menu",
        "Kept app screens persistent",
        "Improved physical button flow",
    };

    return draw_screen_about_lines("CHANGELOG / 0.7.0", lines, SCREEN_MENU_COUNT(lines));
}

static int draw_screen_changelog_v060(void) {
    const char *lines[] = {
        "0.6.0 v62 CPU DIAGNOSTICS",
        "Added cpustress command",
        "Added CPU usage display",
        "Added temperature visibility",
        "Validated usage change under load",
        "Added /dev/null guard",
        "Added /dev/zero guard",
    };

    return draw_screen_about_lines("CHANGELOG / 0.6.0", lines, SCREEN_MENU_COUNT(lines));
}

static int draw_screen_changelog_v051(void) {
    const char *lines[] = {
        "0.5.1 v61 CPU/GPU USAGE HUD",
        "Added CPU usage percent to HUD",
        "Added GPU usage percent to HUD",
        "Read from /sys/kernel/gpu/gpu_busy",
        "Read /proc/stat for CPU idle delta",
        "Display: CPU temp usage GPU temp usage",
        "Verified readout updates live",
    };

    return draw_screen_about_lines("CHANGELOG / 0.5.1", lines, SCREEN_MENU_COUNT(lines));
}

static int draw_screen_changelog_v050(void) {
    const char *lines[] = {
        "0.5.0 v60 NETSERVICE BOOT",
        "Added opt-in boot-time netservice",
        "Flag: /cache/native-init-netservice",
        "Flag absent: ACM only at boot",
        "netservice enable/disable commands",
        "netservice stop/start for reconnect",
        "Validated UDC re-enum + NCM restore",
        "Host NCM interface name may change",
    };

    return draw_screen_about_lines("CHANGELOG / 0.5.0", lines, SCREEN_MENU_COUNT(lines));
}

static int draw_screen_changelog_v041(void) {
    const char *lines[] = {
        "0.4.1 v59 AT SERIAL FILTER",
        "Host modem probe sends AT commands",
        "AT/ATE0/AT+... lines ignored by shell",
        "Filter in native init input path",
        "No bridge-side workaround needed",
        "Stable ACM session under NetworkManager",
    };

    return draw_screen_about_lines("CHANGELOG / 0.4.1", lines, SCREEN_MENU_COUNT(lines));
}

static int draw_screen_changelog_v040(void) {
    const char *lines[] = {
        "0.4.0 v55 NCM TCP CONTROL",
        "USB NCM persistent composite gadget",
        "IPv6 netcat payload verified (v54)",
        "NCM ops helper: a90_usbnet",
        "TCP test helper: a90_nettest",
        "TCP control server: a90_tcpctl",
        "Host wrapper: a90ctl launch/client",
        "Soak validation: 100 round trips",
    };

    return draw_screen_about_lines("CHANGELOG / 0.4.0", lines, SCREEN_MENU_COUNT(lines));
}

static int draw_screen_changelog_v030(void) {
    const char *lines[] = {
        "0.3.0 v53 MENU BUSY GATE",
        "Hardware key menu always visible",
        "VOLUP/DN move POWER select",
        "Menu items: HIDE STATUS LOG",
        "Menu items: RECOVERY REBOOT POWEROFF",
        "Bridge busy gate: hide before recovery",
        "IPC via /tmp/a90-auto-menu-active",
        "bridge hide command clears menu",
    };

    return draw_screen_about_lines("CHANGELOG / 0.3.0", lines, SCREEN_MENU_COUNT(lines));
}

static int draw_screen_changelog_v020(void) {
    const char *lines[] = {
        "0.2.0 v40-v45 SHELL LOG HUD CORE",
        "Shell command dispatch stabilized",
        "Structured logging to /cache",
        "Boot timeline recording",
        "KMS/DRM status HUD: 4 rows scale 5",
        "BAT+PWR combined row",
        "Punch-hole camera y offset",
        "Per-segment label/value color split",
    };

    return draw_screen_about_lines("CHANGELOG / 0.2.0", lines, SCREEN_MENU_COUNT(lines));
}

static int draw_screen_changelog_v010(void) {
    const char *lines[] = {
        "0.1.0 v1 NATIVE INIT ORIGIN",
        "PID 1 native C init confirmed",
        "KMS/DRM dumb buffer rendering",
        "5x7 bitmap font renderer",
        "USB CDC ACM serial shell",
        "TCP bridge 127.0.0.1:54321",
        "Input event probing (event0/3)",
        "Blind menu for button control",
    };

    return draw_screen_about_lines("CHANGELOG / 0.1.0", lines, SCREEN_MENU_COUNT(lines));
}

static int draw_screen_changelog_detail(enum screen_app_id app_id) {
    switch (app_id) {
    case SCREEN_APP_CHANGELOG_0815:
        return draw_screen_changelog_v0815();
    case SCREEN_APP_CHANGELOG_0814:
        return draw_screen_changelog_v0814();
    case SCREEN_APP_CHANGELOG_0813:
        return draw_screen_changelog_v0813();
    case SCREEN_APP_CHANGELOG_0812:
        return draw_screen_changelog_v0812();
    case SCREEN_APP_CHANGELOG_0811:
        return draw_screen_changelog_v0811();
    case SCREEN_APP_CHANGELOG_0810:
        return draw_screen_changelog_v0810();
    case SCREEN_APP_CHANGELOG_089:
        return draw_screen_changelog_v089();
    case SCREEN_APP_CHANGELOG_088:
        return draw_screen_changelog_v088();
    case SCREEN_APP_CHANGELOG_087:
        return draw_screen_changelog_v087();
    case SCREEN_APP_CHANGELOG_086:
        return draw_screen_changelog_v086();
    case SCREEN_APP_CHANGELOG_085:
        return draw_screen_changelog_v085();
    case SCREEN_APP_CHANGELOG_084:
        return draw_screen_changelog_v084();
    case SCREEN_APP_CHANGELOG_083:
        return draw_screen_changelog_v083();
    case SCREEN_APP_CHANGELOG_082:
        return draw_screen_changelog_v082();
    case SCREEN_APP_CHANGELOG_081:
        return draw_screen_changelog_v081();
    case SCREEN_APP_CHANGELOG_080:
        return draw_screen_changelog_v080();
    case SCREEN_APP_CHANGELOG_075:
        return draw_screen_changelog_v075();
    case SCREEN_APP_CHANGELOG_074:
        return draw_screen_changelog_v074();
    case SCREEN_APP_CHANGELOG_073:
        return draw_screen_changelog_v073();
    case SCREEN_APP_CHANGELOG_072:
        return draw_screen_changelog_v072();
    case SCREEN_APP_CHANGELOG_071:
        return draw_screen_changelog_v071();
    case SCREEN_APP_CHANGELOG_070:
        return draw_screen_changelog_v070();
    case SCREEN_APP_CHANGELOG_060:
        return draw_screen_changelog_v060();
    case SCREEN_APP_CHANGELOG_051:
        return draw_screen_changelog_v051();
    case SCREEN_APP_CHANGELOG_050:
        return draw_screen_changelog_v050();
    case SCREEN_APP_CHANGELOG_041:
        return draw_screen_changelog_v041();
    case SCREEN_APP_CHANGELOG_040:
        return draw_screen_changelog_v040();
    case SCREEN_APP_CHANGELOG_030:
        return draw_screen_changelog_v030();
    case SCREEN_APP_CHANGELOG_020:
        return draw_screen_changelog_v020();
    case SCREEN_APP_CHANGELOG_010:
        return draw_screen_changelog_v010();
    default:
        return 0;
    }
}

static int draw_screen_about_credits(void) {
    const char *lines[] = {
        INIT_CREATOR,
        "DEVICE SAMSUNG GALAXY A90 5G",
        "MODEL SM-A908N",
        "KERNEL SAMSUNG STOCK 4.14",
        "CONTROL USB ACM + NCM",
        "PROJECT NATIVE INIT USERSPACE",
    };

    return draw_screen_about_lines("ABOUT / CREDITS", lines, SCREEN_MENU_COUNT(lines));
}

static int draw_screen_network_summary(void) {
    char line1[96];
    char line2[96];
    char line3[96];
    char line4[96];

    snprintf(line1, sizeof(line1), "NETSERVICE %s",
             access(NETSERVICE_FLAG_PATH, F_OK) == 0 ? "ENABLED" : "DISABLED");
    snprintf(line2, sizeof(line2), "%s %s %s",
             NETSERVICE_IFNAME,
             access("/sys/class/net/" NETSERVICE_IFNAME, F_OK) == 0 ? "PRESENT" : "ABSENT",
             NETSERVICE_DEVICE_IP);
    snprintf(line3, sizeof(line3), "TCPCTL %s%s%ld",
             tcpctl_pid > 0 ? "RUNNING PID " : "STOPPED",
             tcpctl_pid > 0 ? "" : "",
             tcpctl_pid > 0 ? (long)tcpctl_pid : 0L);
    if (tcpctl_pid <= 0) {
        snprintf(line3, sizeof(line3), "TCPCTL STOPPED");
    }
    snprintf(line4, sizeof(line4), "PORT %s LOG %s", NETSERVICE_TCP_PORT, NETSERVICE_LOG_PATH);

    return draw_screen_info_page("NETWORK STATUS", line1, line2, line3, line4);
}

static int draw_screen_cpu_hint(void) {
    return draw_screen_info_page("TOOLS / CPU STRESS",
                                 "AUTO MENU: CHOOSE 5/10/30/60S",
                                 "SERIAL: cpustress <sec> 8",
                                 "CPU GAUGE SHOULD RISE",
                                 "GPU MAY STAY 0% ON CPU TEST");
}

static long clamp_stress_duration_ms(long duration_ms) {
    if (duration_ms < 1000L) {
        return 1000L;
    }
    if (duration_ms > 120000L) {
        return 120000L;
    }
    return duration_ms;
}

static int draw_screen_cpu_stress_app(bool running,
                                      bool done,
                                      bool failed,
                                      long remaining_ms,
                                      long duration_ms) {
    struct status_snapshot snapshot;
    char online[64];
    char present[64];
    char freq0[32];
    char freq1[32];
    char freq2[32];
    char freq3[32];
    char freq4[32];
    char freq5[32];
    char freq6[32];
    char freq7[32];
    char lines[8][160];
    const char *status_word;
    uint32_t scale;
    uint32_t title_scale;
    uint32_t x;
    uint32_t y;
    uint32_t card_w;
    uint32_t line_h;
    size_t index;

    duration_ms = clamp_stress_duration_ms(duration_ms);

    if (failed) {
        status_word = "FAILED";
    } else if (running) {
        status_word = "RUNNING";
    } else if (done) {
        status_word = "DONE";
    } else {
        status_word = "READY";
    }

    read_status_snapshot(&snapshot);
    if (read_trimmed_text_file("/sys/devices/system/cpu/online",
                               online,
                               sizeof(online)) < 0) {
        strcpy(online, "?");
    }
    if (read_trimmed_text_file("/sys/devices/system/cpu/present",
                               present,
                               sizeof(present)) < 0) {
        strcpy(present, "?");
    }
    screen_app_read_cpu_freq_label(0, freq0, sizeof(freq0));
    screen_app_read_cpu_freq_label(1, freq1, sizeof(freq1));
    screen_app_read_cpu_freq_label(2, freq2, sizeof(freq2));
    screen_app_read_cpu_freq_label(3, freq3, sizeof(freq3));
    screen_app_read_cpu_freq_label(4, freq4, sizeof(freq4));
    screen_app_read_cpu_freq_label(5, freq5, sizeof(freq5));
    screen_app_read_cpu_freq_label(6, freq6, sizeof(freq6));
    screen_app_read_cpu_freq_label(7, freq7, sizeof(freq7));

    snprintf(lines[0], sizeof(lines[0]), "STATE %s  REM %ld.%03ldS",
             status_word,
             remaining_ms / 1000L,
             remaining_ms % 1000L);
    snprintf(lines[1], sizeof(lines[1]), "CPU %s  USE %s  LOAD %s",
             snapshot.cpu_temp,
             snapshot.cpu_usage,
             snapshot.loadavg);
    snprintf(lines[2], sizeof(lines[2]), "CORES ONLINE %.24s  PRESENT %.24s", online, present);
    snprintf(lines[3], sizeof(lines[3]), "FREQ 0:%s 1:%s 2:%s 3:%s",
             freq0, freq1, freq2, freq3);
    snprintf(lines[4], sizeof(lines[4]), "FREQ 4:%s 5:%s 6:%s 7:%s",
             freq4, freq5, freq6, freq7);
    snprintf(lines[5], sizeof(lines[5]), "MEM %s  PWR %s",
             snapshot.memory,
             snapshot.power_now);
    snprintf(lines[6], sizeof(lines[6]), "WORKERS 8  TEST %ldS", duration_ms / 1000L);
    snprintf(lines[7], sizeof(lines[7]), "ANY BUTTON BACK / CANCEL");

    if (kms_begin_frame(0x050505) < 0) {
        return negative_errno_or(ENODEV);
    }

    scale = menu_text_scale();
    title_scale = scale + 1;
    x = kms_state.width / 18;
    if (x < scale * 4) {
        x = scale * 4;
    }
    y = kms_state.height / 10;
    card_w = kms_state.width - (x * 2);
    line_h = scale * 11;

    kms_draw_text(&kms_state, x, y, "TOOLS / CPU STRESS", 0xffcc33,
                  shrink_text_scale("TOOLS / CPU STRESS", title_scale, card_w));
    y += line_h + scale * 4;

    kms_fill_rect(&kms_state, x - scale, y - scale, card_w, line_h * 9, 0x202020);
    for (index = 0; index < 8; ++index) {
        uint32_t color = 0xffffff;

        if (index == 0) {
            color = failed ? 0xff6666 : (running ? 0x88ee88 : 0xffcc33);
        } else if (index == 7) {
            color = 0xdddddd;
        }
        kms_draw_text(&kms_state, x, y + (uint32_t)index * line_h,
                      lines[index],
                      color,
                      shrink_text_scale(lines[index], scale, card_w - scale * 2));
    }

    if (kms_present_frame("cpustress") < 0) {
        return negative_errno_or(EIO);
    }
    return 0;
}

static int wait_for_menu_return(struct key_wait_context *ctx, const char *tag) {
    struct input_gesture gesture;
    int wait_rc = wait_for_input_gesture(ctx, tag, &gesture);

    if (wait_rc < 0) {
        return wait_rc;
    }
    return 0;
}

static void restore_auto_hud_if_needed(bool restore_hud) {
    if (restore_hud) {
        if (start_auto_hud(BOOT_HUD_REFRESH_SECONDS, false) < 0) {
            a90_logf("screenmenu", "autohud restore failed errno=%d error=%s",
                        errno, strerror(errno));
        }
    }
}

static int cmd_blindmenu(void) {
    static const struct blind_menu_item items[] = {
        { "resume", "return to shell prompt" },
        { "recovery", "reboot to TWRP recovery" },
        { "reboot", "restart device" },
        { "poweroff", "power off device" },
    };
    struct key_wait_context ctx;
    size_t selected = 0;
    size_t count = sizeof(items) / sizeof(items[0]);

    if (open_key_wait_context(&ctx, "blindmenu") < 0) {
        return negative_errno_or(ENOENT);
    }

    a90_console_printf("blindmenu: VOLUP=prev VOLDOWN=next POWER=select dbl/COMBO=back q/Ctrl-C=cancel\r\n");
    a90_console_printf("blindmenu: start with a safe default, then move as needed\r\n");
    print_blind_menu_selection(items, count, selected);

    while (1) {
        struct input_gesture gesture;
        enum input_menu_action menu_action;

        int wait_rc = wait_for_input_gesture(&ctx, "blindmenu", &gesture);

        if (wait_rc < 0) {
            close_key_wait_context(&ctx);
            return wait_rc;
        }

        menu_action = input_menu_action_from_gesture(&gesture);

        if (menu_action == INPUT_MENU_ACTION_PREV ||
            menu_action == INPUT_MENU_ACTION_PAGE_PREV) {
            size_t step = menu_action == INPUT_MENU_ACTION_PAGE_PREV ?
                          INPUT_PAGE_STEP : 1;

            selected = (selected + count - (step % count)) % count;
            print_blind_menu_selection(items, count, selected);
            continue;
        }

        if (menu_action == INPUT_MENU_ACTION_NEXT ||
            menu_action == INPUT_MENU_ACTION_PAGE_NEXT) {
            size_t step = menu_action == INPUT_MENU_ACTION_PAGE_NEXT ?
                          INPUT_PAGE_STEP : 1;

            selected = (selected + step) % count;
            print_blind_menu_selection(items, count, selected);
            continue;
        }

        if (menu_action == INPUT_MENU_ACTION_BACK ||
            menu_action == INPUT_MENU_ACTION_HIDE) {
            a90_console_printf("blindmenu: leaving menu\r\n");
            close_key_wait_context(&ctx);
            return 0;
        }

        if (menu_action == INPUT_MENU_ACTION_RESERVED) {
            a90_console_printf("blindmenu: reserved gesture ignored for safety\r\n");
            continue;
        }

        if (menu_action != INPUT_MENU_ACTION_SELECT) {
            a90_console_printf("blindmenu: ignoring gesture %s\r\n",
                    input_gesture_name(gesture.id));
            continue;
        }

        a90_console_printf("blindmenu: selected %s\r\n", items[selected].name);
        close_key_wait_context(&ctx);

        if (selected == 0) {
            a90_console_printf("blindmenu: leaving menu\r\n");
            return 0;
        }
        if (selected == 1) {
            return cmd_recovery();
        }
        if (selected == 2) {
            sync();
            reboot(RB_AUTOBOOT);
            wf("/proc/sysrq-trigger", "b");
            return negative_errno_or(EIO);
        }

        sync();
        reboot(RB_POWER_OFF);
        return negative_errno_or(EIO);
    }

    close_key_wait_context(&ctx);
    return 0;
}

static int cmd_screenmenu(void) {
    struct key_wait_context ctx;
    enum screen_menu_page_id current_page = SCREEN_MENU_PAGE_MAIN;
    const struct screen_menu_page *page = screen_menu_get_page(current_page);
    size_t selected = 0;
    bool restore_hud;
    int draw_rc;

    reap_hud_child();
    restore_hud = hud_pid > 0;
    stop_auto_hud(false);

    if (open_key_wait_context(&ctx, "screenmenu") < 0) {
        restore_auto_hud_if_needed(restore_hud);
        return negative_errno_or(ENOENT);
    }

    a90_console_printf("screenmenu: VOLUP=prev VOLDOWN=next POWER=select dbl/COMBO=back q/Ctrl-C=cancel\r\n");
    a90_logf("screenmenu", "start restore_hud=%d", restore_hud ? 1 : 0);
    print_screen_menu_selection(page, selected);

    draw_rc = draw_screen_menu(page, selected);
    if (draw_rc < 0) {
        close_key_wait_context(&ctx);
        restore_auto_hud_if_needed(restore_hud);
        return draw_rc;
    }

    while (1) {
        struct input_gesture gesture;
        enum input_menu_action menu_action;
        int wait_rc = wait_for_input_gesture(&ctx, "screenmenu", &gesture);

        if (wait_rc < 0) {
            close_key_wait_context(&ctx);
            restore_auto_hud_if_needed(restore_hud);
            return wait_rc;
        }

        menu_action = input_menu_action_from_gesture(&gesture);

        if (menu_action == INPUT_MENU_ACTION_PREV ||
            menu_action == INPUT_MENU_ACTION_PAGE_PREV) {
            size_t step = menu_action == INPUT_MENU_ACTION_PAGE_PREV ?
                          INPUT_PAGE_STEP : 1;

            page = screen_menu_get_page(current_page);
            selected = (selected + page->count - (step % page->count)) % page->count;
            print_screen_menu_selection(page, selected);
            draw_rc = draw_screen_menu(page, selected);
            if (draw_rc < 0) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(restore_hud);
                return draw_rc;
            }
            continue;
        }

        if (menu_action == INPUT_MENU_ACTION_NEXT ||
            menu_action == INPUT_MENU_ACTION_PAGE_NEXT) {
            size_t step = menu_action == INPUT_MENU_ACTION_PAGE_NEXT ?
                          INPUT_PAGE_STEP : 1;

            page = screen_menu_get_page(current_page);
            selected = (selected + step) % page->count;
            print_screen_menu_selection(page, selected);
            draw_rc = draw_screen_menu(page, selected);
            if (draw_rc < 0) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(restore_hud);
                return draw_rc;
            }
            continue;
        }

        if (menu_action == INPUT_MENU_ACTION_BACK) {
            page = screen_menu_get_page(current_page);
            if (current_page == SCREEN_MENU_PAGE_MAIN) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(restore_hud);
                return 0;
            }
            current_page = page->parent;
            page = screen_menu_get_page(current_page);
            selected = 0;
            print_screen_menu_selection(page, selected);
            draw_rc = draw_screen_menu(page, selected);
            if (draw_rc < 0) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(restore_hud);
                return draw_rc;
            }
            continue;
        }

        if (menu_action == INPUT_MENU_ACTION_HIDE) {
            close_key_wait_context(&ctx);
            restore_auto_hud_if_needed(restore_hud);
            return 0;
        }

        if (menu_action == INPUT_MENU_ACTION_STATUS) {
            draw_rc = cmd_statushud();
            if (draw_rc < 0) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(restore_hud);
                return draw_rc;
            }
            a90_console_printf("screenmenu: status shortcut shown, press any button to return\r\n");
            wait_rc = wait_for_menu_return(&ctx, "screenmenu");
            if (wait_rc < 0) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(restore_hud);
                return wait_rc;
            }
            page = screen_menu_get_page(current_page);
            draw_rc = draw_screen_menu(page, selected);
            if (draw_rc < 0) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(restore_hud);
                return draw_rc;
            }
            continue;
        }

        if (menu_action == INPUT_MENU_ACTION_LOG) {
            draw_rc = draw_screen_log_summary();
            if (draw_rc < 0) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(restore_hud);
                return draw_rc;
            }
            a90_console_printf("screenmenu: log shortcut shown, press any button to return\r\n");
            wait_rc = wait_for_menu_return(&ctx, "screenmenu");
            if (wait_rc < 0) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(restore_hud);
                return wait_rc;
            }
            page = screen_menu_get_page(current_page);
            draw_rc = draw_screen_menu(page, selected);
            if (draw_rc < 0) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(restore_hud);
                return draw_rc;
            }
            continue;
        }

        if (menu_action == INPUT_MENU_ACTION_RESERVED) {
            a90_console_printf("screenmenu: reserved gesture ignored for safety\r\n");
            continue;
        }

        if (menu_action != INPUT_MENU_ACTION_SELECT) {
            a90_console_printf("screenmenu: ignoring gesture %s\r\n",
                    input_gesture_name(gesture.id));
            continue;
        }

        page = screen_menu_get_page(current_page);
        a90_console_printf("screenmenu: selected %s / %s\r\n", page->title, page->items[selected].name);
        a90_logf("screenmenu", "selected page=%s item=%s",
                    page->title, page->items[selected].name);

        if (page->items[selected].action == SCREEN_MENU_RESUME) {
            close_key_wait_context(&ctx);
            restore_auto_hud_if_needed(restore_hud);
            return 0;
        }

        if (page->items[selected].action == SCREEN_MENU_SUBMENU) {
            current_page = page->items[selected].target;
            page = screen_menu_get_page(current_page);
            selected = 0;
            print_screen_menu_selection(page, selected);
            draw_rc = draw_screen_menu(page, selected);
            if (draw_rc < 0) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(restore_hud);
                return draw_rc;
            }
            continue;
        }

        if (page->items[selected].action == SCREEN_MENU_BACK) {
            current_page = page->parent;
            page = screen_menu_get_page(current_page);
            selected = 0;
            print_screen_menu_selection(page, selected);
            draw_rc = draw_screen_menu(page, selected);
            if (draw_rc < 0) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(restore_hud);
                return draw_rc;
            }
            continue;
        }

        if (page->items[selected].action == SCREEN_MENU_STATUS) {
            draw_rc = cmd_statushud();
            if (draw_rc < 0) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(restore_hud);
                return draw_rc;
            }
            a90_console_printf("screenmenu: status shown, press any button to return\r\n");
            wait_rc = wait_for_menu_return(&ctx, "screenmenu");
            if (wait_rc < 0) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(restore_hud);
                return wait_rc;
            }
            page = screen_menu_get_page(current_page);
            draw_rc = draw_screen_menu(page, selected);
            if (draw_rc < 0) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(restore_hud);
                return draw_rc;
            }
            continue;
        }

        if (page->items[selected].action == SCREEN_MENU_LOG) {
            draw_rc = draw_screen_log_summary();
            if (draw_rc < 0) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(restore_hud);
                return draw_rc;
            }
            a90_console_printf("screenmenu: log summary shown, press any button to return\r\n");
            wait_rc = wait_for_menu_return(&ctx, "screenmenu");
            if (wait_rc < 0) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(restore_hud);
                return wait_rc;
            }
            page = screen_menu_get_page(current_page);
            draw_rc = draw_screen_menu(page, selected);
            if (draw_rc < 0) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(restore_hud);
                return draw_rc;
            }
            continue;
        }

        if (page->items[selected].action == SCREEN_MENU_NET_STATUS) {
            draw_rc = draw_screen_network_summary();
            if (draw_rc < 0) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(restore_hud);
                return draw_rc;
            }
            a90_console_printf("screenmenu: network shown, press any button to return\r\n");
            wait_rc = wait_for_menu_return(&ctx, "screenmenu");
            if (wait_rc < 0) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(restore_hud);
                return wait_rc;
            }
            page = screen_menu_get_page(current_page);
            draw_rc = draw_screen_menu(page, selected);
            if (draw_rc < 0) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(restore_hud);
                return draw_rc;
            }
            continue;
        }

        if (page->items[selected].action == SCREEN_MENU_INPUT_MONITOR) {
            char *monitor_argv[] = { "inputmonitor", "0" };

            close_key_wait_context(&ctx);
            restore_auto_hud_if_needed(restore_hud);
            return cmd_inputmonitor(monitor_argv, 2);
        }

        if (page->items[selected].action == SCREEN_MENU_DISPLAY_TEST) {
            draw_rc = draw_screen_display_test();
            if (draw_rc < 0) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(restore_hud);
                return draw_rc;
            }
            a90_console_printf("screenmenu: display test shown, press any button to return\r\n");
            wait_rc = wait_for_menu_return(&ctx, "screenmenu");
            if (wait_rc < 0) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(restore_hud);
                return wait_rc;
            }
            page = screen_menu_get_page(current_page);
            draw_rc = draw_screen_menu(page, selected);
            if (draw_rc < 0) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(restore_hud);
                return draw_rc;
            }
            continue;
        }

        {
            enum screen_app_id about_app = screen_menu_about_app(page->items[selected].action);

            if (about_app != SCREEN_APP_NONE) {
                draw_rc = draw_screen_about_app(about_app);
                if (draw_rc < 0) {
                    close_key_wait_context(&ctx);
                    restore_auto_hud_if_needed(restore_hud);
                    return draw_rc;
                }
                a90_console_printf("screenmenu: about shown, press any button to return\r\n");
                wait_rc = wait_for_menu_return(&ctx, "screenmenu");
                if (wait_rc < 0) {
                    close_key_wait_context(&ctx);
                    restore_auto_hud_if_needed(restore_hud);
                    return wait_rc;
                }
                page = screen_menu_get_page(current_page);
                draw_rc = draw_screen_menu(page, selected);
                if (draw_rc < 0) {
                    close_key_wait_context(&ctx);
                    restore_auto_hud_if_needed(restore_hud);
                    return draw_rc;
                }
                continue;
            }
        }

        if (screen_menu_cpu_stress_seconds(page->items[selected].action) > 0) {
            draw_rc = draw_screen_cpu_hint();
            if (draw_rc < 0) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(restore_hud);
                return draw_rc;
            }
            a90_console_printf("screenmenu: CPU stress help shown, press any button to return\r\n");
            wait_rc = wait_for_menu_return(&ctx, "screenmenu");
            if (wait_rc < 0) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(restore_hud);
                return wait_rc;
            }
            page = screen_menu_get_page(current_page);
            draw_rc = draw_screen_menu(page, selected);
            if (draw_rc < 0) {
                close_key_wait_context(&ctx);
                restore_auto_hud_if_needed(restore_hud);
                return draw_rc;
            }
            continue;
        }

        close_key_wait_context(&ctx);

        if (page->items[selected].action == SCREEN_MENU_RECOVERY) {
            return cmd_recovery();
        }
        if (page->items[selected].action == SCREEN_MENU_REBOOT) {
            a90_console_printf("screenmenu: syncing and restarting\r\n");
            sync();
            reboot(RB_AUTOBOOT);
            wf("/proc/sysrq-trigger", "b");
            return negative_errno_or(EIO);
        }

        a90_console_printf("screenmenu: syncing and powering off\r\n");
        sync();
        reboot(RB_POWER_OFF);
        return negative_errno_or(EIO);
    }
}

static int ensure_char_node_exact(const char *path, unsigned int major_num, unsigned int minor_num) {
    dev_t wanted = makedev(major_num, minor_num);
    struct stat st;

    if (lstat(path, &st) == 0) {
        if (S_ISCHR(st.st_mode) && st.st_rdev == wanted) {
            return 0;
        }
        if (unlink(path) < 0) {
            return -1;
        }
    } else if (errno != ENOENT) {
        return -1;
    }

    if (mknod(path, S_IFCHR | 0600, wanted) == 0 || errno == EEXIST) {
        return 0;
    }

    return -1;
}
