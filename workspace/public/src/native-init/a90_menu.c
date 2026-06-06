#include "a90_menu.h"

#include <stdio.h>

#include "a90_changelog.h"

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
    { "CHANGELOG >", "VERSION SERIES",  SCREEN_MENU_SUBMENU,        SCREEN_MENU_PAGE_CHANGELOG_SERIES },
    { "CREDITS",     "MADE BY",         SCREEN_MENU_ABOUT_CREDITS,  SCREEN_MENU_PAGE_ABOUT },
    { "BACK",        "APPS",            SCREEN_MENU_BACK,           SCREEN_MENU_PAGE_APPS },
};

static struct screen_menu_item screen_menu_changelog_series_items[A90_CHANGELOG_MAX_SERIES + 1];
static struct screen_menu_page screen_menu_changelog_series_page = {
    "ABOUT / CHANGELOG",
    screen_menu_changelog_series_items,
    0,
    SCREEN_MENU_PAGE_ABOUT,
};
static bool screen_menu_changelog_series_ready;

static struct screen_menu_item screen_menu_changelog_items[A90_CHANGELOG_MAX_ENTRIES + 1];
static char screen_menu_changelog_title[48];
static struct screen_menu_page screen_menu_changelog_page = {
    screen_menu_changelog_title,
    screen_menu_changelog_items,
    0,
    SCREEN_MENU_PAGE_CHANGELOG_SERIES,
};
static size_t screen_menu_changelog_series_index;
static size_t screen_menu_changelog_ready_series = (size_t)-1;

static void screen_menu_init_changelog_series_page(void) {
    size_t count;
    size_t index;

    if (screen_menu_changelog_series_ready) {
        return;
    }

    count = a90_changelog_series_count();
    if (count > A90_CHANGELOG_MAX_SERIES) {
        count = A90_CHANGELOG_MAX_SERIES;
    }

    for (index = 0; index < count; ++index) {
        const struct a90_changelog_series *series = a90_changelog_series_at(index);

        screen_menu_changelog_series_items[index].name =
            series != NULL ? series->label : "UNKNOWN";
        screen_menu_changelog_series_items[index].summary =
            series != NULL ? series->summary : "CHANGELOG";
        screen_menu_changelog_series_items[index].action = SCREEN_MENU_CHANGELOG_SERIES;
        screen_menu_changelog_series_items[index].target = SCREEN_MENU_PAGE_CHANGELOG;
    }

    screen_menu_changelog_series_items[count].name = "BACK";
    screen_menu_changelog_series_items[count].summary = "ABOUT";
    screen_menu_changelog_series_items[count].action = SCREEN_MENU_BACK;
    screen_menu_changelog_series_items[count].target = SCREEN_MENU_PAGE_ABOUT;
    screen_menu_changelog_series_page.count = count + 1;
    screen_menu_changelog_series_ready = true;
}

static void screen_menu_init_changelog_page(void) {
    size_t count;
    size_t index;
    const struct a90_changelog_series *series;

    if (screen_menu_changelog_ready_series == screen_menu_changelog_series_index) {
        return;
    }

    series = a90_changelog_series_at(screen_menu_changelog_series_index);
    snprintf(screen_menu_changelog_title,
             sizeof(screen_menu_changelog_title),
             "CHANGELOG / %s",
             series != NULL ? series->label : "UNKNOWN");

    count = a90_changelog_series_entry_count(screen_menu_changelog_series_index);
    if (count > A90_CHANGELOG_MAX_ENTRIES) {
        count = A90_CHANGELOG_MAX_ENTRIES;
    }

    for (index = 0; index < count; ++index) {
        size_t entry_index = a90_changelog_entry_index_for_series(screen_menu_changelog_series_index,
                                                                  index);
        const struct a90_changelog_entry *entry = a90_changelog_entry_at(entry_index);

        screen_menu_changelog_items[index].name = entry != NULL ? entry->label : "UNKNOWN";
        screen_menu_changelog_items[index].summary = entry != NULL ? entry->summary : "CHANGELOG";
        screen_menu_changelog_items[index].action = SCREEN_MENU_CHANGELOG_ENTRY;
        screen_menu_changelog_items[index].target = SCREEN_MENU_PAGE_CHANGELOG;
    }

    screen_menu_changelog_items[count].name = "BACK";
    screen_menu_changelog_items[count].summary = "ABOUT";
    screen_menu_changelog_items[count].action = SCREEN_MENU_BACK;
    screen_menu_changelog_items[count].target = SCREEN_MENU_PAGE_CHANGELOG_SERIES;
    screen_menu_changelog_page.count = count + 1;
    screen_menu_changelog_ready_series = screen_menu_changelog_series_index;
}

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
    [SCREEN_MENU_PAGE_CHANGELOG_SERIES] = {
        "ABOUT / CHANGELOG", screen_menu_changelog_series_items,
        0, SCREEN_MENU_PAGE_ABOUT
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

const struct screen_menu_page *a90_menu_page(enum screen_menu_page_id page_id) {
    if ((int)page_id < 0 || page_id >= SCREEN_MENU_PAGE_COUNT) {
        page_id = SCREEN_MENU_PAGE_MAIN;
    }
    if (page_id == SCREEN_MENU_PAGE_CHANGELOG_SERIES) {
        screen_menu_init_changelog_series_page();
        return &screen_menu_changelog_series_page;
    }
    if (page_id == SCREEN_MENU_PAGE_CHANGELOG) {
        screen_menu_init_changelog_page();
        return &screen_menu_changelog_page;
    }
    return &screen_menu_pages[page_id];
}

long a90_menu_cpu_stress_seconds(enum screen_menu_action action) {
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

enum screen_app_id a90_menu_app_from_action(enum screen_menu_action action) {
    switch (action) {
    case SCREEN_MENU_ABOUT_VERSION:
        return SCREEN_APP_ABOUT_VERSION;
    case SCREEN_MENU_ABOUT_CHANGELOG:
        return SCREEN_APP_ABOUT_CHANGELOG;
    case SCREEN_MENU_ABOUT_CREDITS:
        return SCREEN_APP_ABOUT_CREDITS;
    case SCREEN_MENU_CHANGELOG_ENTRY:
        return SCREEN_APP_CHANGELOG_DETAIL;
    default:
        return SCREEN_APP_NONE;
    }
}

bool a90_menu_action_opens_app(enum screen_menu_action action, enum screen_app_id *out) {
    enum screen_app_id app_id = a90_menu_app_from_action(action);

    if (out != NULL) {
        *out = app_id;
    }
    return app_id != SCREEN_APP_NONE;
}


void a90_menu_state_init(struct a90_menu_state *state) {
    if (state == NULL) {
        return;
    }
    state->page = SCREEN_MENU_PAGE_MAIN;
    state->selected = 0;
}

const struct screen_menu_page *a90_menu_state_page(const struct a90_menu_state *state) {
    if (state == NULL) {
        return a90_menu_page(SCREEN_MENU_PAGE_MAIN);
    }
    return a90_menu_page(state->page);
}

enum screen_menu_page_id a90_menu_state_page_id(const struct a90_menu_state *state) {
    if (state == NULL) {
        return SCREEN_MENU_PAGE_MAIN;
    }
    return state->page;
}

size_t a90_menu_state_selected_index(const struct a90_menu_state *state) {
    const struct screen_menu_page *page;

    if (state == NULL) {
        return 0;
    }
    page = a90_menu_page(state->page);
    if (page->count == 0) {
        return 0;
    }
    if (state->selected >= page->count) {
        return page->count - 1;
    }
    return state->selected;
}

const struct screen_menu_item *a90_menu_state_selected(const struct a90_menu_state *state) {
    const struct screen_menu_page *page = a90_menu_state_page(state);
    size_t selected = a90_menu_state_selected_index(state);

    if (page->count == 0) {
        return NULL;
    }
    return &page->items[selected];
}

void a90_menu_state_move(struct a90_menu_state *state, int delta) {
    const struct screen_menu_page *page;
    long selected;
    long count;

    if (state == NULL) {
        return;
    }
    page = a90_menu_page(state->page);
    if (page->count == 0) {
        state->selected = 0;
        return;
    }
    count = (long)page->count;
    selected = (long)a90_menu_state_selected_index(state) + (long)delta;
    selected %= count;
    if (selected < 0) {
        selected += count;
    }
    state->selected = (size_t)selected;
}

void a90_menu_state_set_page(struct a90_menu_state *state,
                             enum screen_menu_page_id page_id) {
    if (state == NULL) {
        return;
    }
    if ((int)page_id < 0 || page_id >= SCREEN_MENU_PAGE_COUNT) {
        page_id = SCREEN_MENU_PAGE_MAIN;
    }
    state->page = page_id;
    state->selected = 0;
}

bool a90_menu_state_back(struct a90_menu_state *state) {
    const struct screen_menu_page *page;

    if (state == NULL) {
        return false;
    }
    page = a90_menu_page(state->page);
    if (state->page == SCREEN_MENU_PAGE_MAIN) {
        state->selected = 0;
        return false;
    }
    state->page = page->parent;
    state->selected = 0;
    return true;
}

bool a90_menu_app_is_changelog(enum screen_app_id app_id) {
    return app_id == SCREEN_APP_CHANGELOG_DETAIL;
}

bool a90_menu_page_is_changelog(enum screen_menu_page_id page_id) {
    return page_id == SCREEN_MENU_PAGE_CHANGELOG ||
           page_id == SCREEN_MENU_PAGE_CHANGELOG_SERIES;
}

bool a90_menu_app_is_about(enum screen_app_id app_id) {
    switch (app_id) {
    case SCREEN_APP_ABOUT_VERSION:
    case SCREEN_APP_ABOUT_CHANGELOG:
    case SCREEN_APP_ABOUT_CREDITS:
        return true;
    default:
        return a90_menu_app_is_changelog(app_id);
    }
}

void a90_menu_set_changelog_series(size_t series_index) {
    if (series_index >= a90_changelog_series_count()) {
        series_index = 0;
    }
    if (screen_menu_changelog_series_index != series_index) {
        screen_menu_changelog_ready_series = (size_t)-1;
    }
    screen_menu_changelog_series_index = series_index;
}

size_t a90_menu_changelog_series(void) {
    return screen_menu_changelog_series_index;
}

size_t a90_menu_changelog_series_for_selected_index(size_t selected) {
    if (selected >= a90_changelog_series_count()) {
        return (size_t)-1;
    }
    return selected;
}

size_t a90_menu_changelog_entry_index_for_selected(size_t selected) {
    return a90_changelog_entry_index_for_series(screen_menu_changelog_series_index,
                                                selected);
}
