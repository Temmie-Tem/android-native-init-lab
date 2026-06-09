#ifndef A90_APP_WIFI_H
#define A90_APP_WIFI_H

#include "a90_menu.h"

void a90_app_wifi_reset(enum screen_app_id app_id);
int a90_app_wifi_draw_status(void);
int a90_app_wifi_draw_profiles(void);
int a90_app_wifi_draw_scan(void);
int a90_app_wifi_draw_ping(void);

#endif
