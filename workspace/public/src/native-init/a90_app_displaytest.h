#ifndef A90_APP_DISPLAYTEST_H
#define A90_APP_DISPLAYTEST_H

#include <stdbool.h>
#include <linux/input.h>

#include "a90_hud.h"

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

struct a90_app_cutout_calibration {
    struct cutout_calibration_state cal;
    unsigned int down_mask;
    long power_down_ms;
    long last_power_up_ms;
};

int a90_app_displaytest_draw_page(unsigned int page_index,
                                  const struct a90_hud_storage_status *storage);
int a90_app_displaytest_draw_cutout_calibration(const struct cutout_calibration_state *cal,
                                                bool interactive);
void a90_app_displaytest_cutout_default(struct cutout_calibration_state *cal);
void a90_app_displaytest_cutout_clamp(struct cutout_calibration_state *cal);
void a90_app_displaytest_cutout_reset(struct a90_app_cutout_calibration *state);
bool a90_app_displaytest_cutout_feed_event(struct a90_app_cutout_calibration *state,
                                           const struct input_event *event);
int a90_app_displaytest_cutout_draw(const struct a90_app_cutout_calibration *state,
                                    bool interactive);
const char *a90_app_displaytest_page_title(unsigned int page_index);

#endif
