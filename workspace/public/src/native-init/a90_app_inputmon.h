#ifndef A90_APP_INPUTMON_H
#define A90_APP_INPUTMON_H

#include <stdbool.h>
#include <linux/input.h>

#include "a90_input.h"

#define A90_INPUTMON_ROWS 9

struct a90_app_inputmon_raw_entry {
    char title[64];
    char detail[96];
    int value;
};

struct a90_app_inputmon_state {
    struct a90_input_decoder decoder;
    struct a90_app_inputmon_raw_entry raw_entries[A90_INPUTMON_ROWS];
    char gesture_title[80];
    char gesture_detail[128];
    char gesture_mask[64];
    enum a90_input_gesture_id gesture_id;
    enum a90_input_menu_action gesture_action;
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

void a90_app_inputmon_reset_state(struct a90_app_inputmon_state *monitor);
bool a90_app_inputmon_feed_state(struct a90_app_inputmon_state *monitor,
                                 const struct input_event *event,
                                 int source_index,
                                 bool serial_echo,
                                 bool exit_on_all_buttons);
void a90_app_inputmon_tick_state(struct a90_app_inputmon_state *monitor,
                                 bool serial_echo);
int a90_app_inputmon_draw_state(const struct a90_app_inputmon_state *monitor);
int a90_app_inputmon_draw_layout(void);

struct a90_app_inputmon_foreground_hooks {
    void (*prepare)(void *userdata);
    void (*restore)(void *userdata, bool restore_hud);
    void *userdata;
};

int a90_app_inputmon_run_foreground(
    char **argv,
    int argc,
    const struct a90_app_inputmon_foreground_hooks *hooks);

#endif
