#ifndef A90_INPUT_H
#define A90_INPUT_H

#include <stdbool.h>
#include <stddef.h>
#include <linux/input.h>

#define A90_INPUT_BUTTON_VOLUP   0x01u
#define A90_INPUT_BUTTON_VOLDOWN 0x02u
#define A90_INPUT_BUTTON_POWER   0x04u
#define A90_INPUT_DOUBLE_CLICK_MS 350L
#define A90_INPUT_LONG_PRESS_MS 800L
#define A90_INPUT_PAGE_STEP 5

enum a90_input_gesture_id {
    A90_INPUT_GESTURE_NONE = 0,
    A90_INPUT_GESTURE_VOLUP_CLICK,
    A90_INPUT_GESTURE_VOLDOWN_CLICK,
    A90_INPUT_GESTURE_POWER_CLICK,
    A90_INPUT_GESTURE_VOLUP_DOUBLE,
    A90_INPUT_GESTURE_VOLDOWN_DOUBLE,
    A90_INPUT_GESTURE_POWER_DOUBLE,
    A90_INPUT_GESTURE_VOLUP_LONG,
    A90_INPUT_GESTURE_VOLDOWN_LONG,
    A90_INPUT_GESTURE_POWER_LONG,
    A90_INPUT_GESTURE_VOLUP_VOLDOWN,
    A90_INPUT_GESTURE_VOLUP_POWER,
    A90_INPUT_GESTURE_VOLDOWN_POWER,
    A90_INPUT_GESTURE_ALL_BUTTONS,
};

enum a90_input_menu_action {
    A90_INPUT_MENU_ACTION_NONE = 0,
    A90_INPUT_MENU_ACTION_PREV,
    A90_INPUT_MENU_ACTION_NEXT,
    A90_INPUT_MENU_ACTION_SELECT,
    A90_INPUT_MENU_ACTION_BACK,
    A90_INPUT_MENU_ACTION_HIDE,
    A90_INPUT_MENU_ACTION_PAGE_PREV,
    A90_INPUT_MENU_ACTION_PAGE_NEXT,
    A90_INPUT_MENU_ACTION_STATUS,
    A90_INPUT_MENU_ACTION_LOG,
    A90_INPUT_MENU_ACTION_RESERVED,
};

struct a90_input_context {
    int fd0;
    int fd3;
};

struct a90_input_gesture {
    enum a90_input_gesture_id id;
    unsigned int code;
    unsigned int mask;
    unsigned int clicks;
    long duration_ms;
};

struct a90_input_decoder {
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

const char *a90_input_key_name(unsigned int code);
unsigned int a90_input_button_mask_from_key(unsigned int code);
void a90_input_mask_text(unsigned int mask, char *buf, size_t buf_size);
void a90_input_gesture_set(struct a90_input_gesture *gesture,
                           enum a90_input_gesture_id id,
                           unsigned int code,
                           unsigned int mask,
                           unsigned int clicks,
                           long duration_ms);
const char *a90_input_gesture_name(enum a90_input_gesture_id id);
enum a90_input_menu_action a90_input_menu_action_from_gesture(
        const struct a90_input_gesture *gesture);
const char *a90_input_menu_action_name(enum a90_input_menu_action action);

int a90_input_open(struct a90_input_context *ctx, const char *tag);
void a90_input_close(struct a90_input_context *ctx);
int a90_input_poll_event(struct a90_input_context *ctx,
                         const char *tag,
                         int timeout_ms,
                         bool allow_console_cancel,
                         struct input_event *event_out,
                         int *source_index_out);
int a90_input_wait_key_press(struct a90_input_context *ctx,
                             const char *tag,
                             unsigned int *code_out);
int a90_input_wait_gesture(struct a90_input_context *ctx,
                           const char *tag,
                           struct a90_input_gesture *gesture);

void a90_input_decoder_init(struct a90_input_decoder *decoder);
int a90_input_decoder_timeout_ms(const struct a90_input_decoder *decoder);
bool a90_input_decoder_emit_pending_if_due(struct a90_input_decoder *decoder,
                                           struct a90_input_gesture *gesture);
bool a90_input_decoder_feed(struct a90_input_decoder *decoder,
                            const struct input_event *event,
                            long now_ms,
                            struct a90_input_gesture *gesture);
void a90_input_print_layout(void);

#endif
