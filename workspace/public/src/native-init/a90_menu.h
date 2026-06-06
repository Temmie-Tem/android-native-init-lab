#ifndef A90_MENU_H
#define A90_MENU_H

#include <stdbool.h>
#include <stddef.h>

enum screen_menu_page_id {
    SCREEN_MENU_PAGE_MAIN = 0,
    SCREEN_MENU_PAGE_APPS,
    SCREEN_MENU_PAGE_ABOUT,
    SCREEN_MENU_PAGE_CHANGELOG_SERIES,
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
    SCREEN_MENU_CHANGELOG_SERIES,
    SCREEN_MENU_CHANGELOG_ENTRY,
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
    SCREEN_APP_CHANGELOG_DETAIL,
    SCREEN_APP_INPUT_MONITOR,
    SCREEN_APP_DISPLAY_TEST,
    SCREEN_APP_CUTOUT_CAL,
    SCREEN_APP_CPU_STRESS,
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

struct a90_menu_state {
    enum screen_menu_page_id page;
    size_t selected;
};

#define SCREEN_MENU_COUNT(items) (sizeof(items) / sizeof((items)[0]))

void a90_menu_state_init(struct a90_menu_state *state);
const struct screen_menu_page *a90_menu_page(enum screen_menu_page_id page_id);
const struct screen_menu_page *a90_menu_state_page(const struct a90_menu_state *state);
enum screen_menu_page_id a90_menu_state_page_id(const struct a90_menu_state *state);
size_t a90_menu_state_selected_index(const struct a90_menu_state *state);
const struct screen_menu_item *a90_menu_state_selected(const struct a90_menu_state *state);
void a90_menu_state_move(struct a90_menu_state *state, int delta);
void a90_menu_state_set_page(struct a90_menu_state *state,
                             enum screen_menu_page_id page_id);
bool a90_menu_state_back(struct a90_menu_state *state);
enum screen_app_id a90_menu_app_from_action(enum screen_menu_action action);
bool a90_menu_action_opens_app(enum screen_menu_action action, enum screen_app_id *out);
bool a90_menu_app_is_changelog(enum screen_app_id app_id);
bool a90_menu_app_is_about(enum screen_app_id app_id);
bool a90_menu_page_is_changelog(enum screen_menu_page_id page_id);
void a90_menu_set_changelog_series(size_t series_index);
size_t a90_menu_changelog_series(void);
size_t a90_menu_changelog_series_for_selected_index(size_t selected);
size_t a90_menu_changelog_entry_index_for_selected(size_t selected);
long a90_menu_cpu_stress_seconds(enum screen_menu_action action);

#endif
