#ifndef A90_APP_ABOUT_H
#define A90_APP_ABOUT_H

#include <stddef.h>

#include "a90_menu.h"

int a90_app_about_draw(enum screen_app_id app_id);
int a90_app_about_draw_paged(enum screen_app_id app_id, size_t changelog_index, size_t page);
int a90_app_about_draw_version(void);
int a90_app_about_draw_changelog(void);
int a90_app_about_draw_changelog_paged(size_t page);
int a90_app_about_draw_changelog_detail_index(size_t index, size_t page);
int a90_app_about_draw_credits(void);
size_t a90_app_about_page_count(enum screen_app_id app_id, size_t changelog_index);

#endif
