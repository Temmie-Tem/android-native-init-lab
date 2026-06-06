#include "a90_app_inputmon.h"

#include <errno.h>
#include <poll.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

#include "a90_console.h"
#include "a90_draw.h"
#include "a90_kms.h"
#include "a90_log.h"
#include "a90_util.h"

#define A90_APP_INPUTMON_COUNT(items) (sizeof(items) / sizeof((items)[0]))

static uint32_t app_inputmon_width_or(uint32_t fallback) {
    struct a90_kms_info info;

    a90_kms_info(&info);
    return info.width > 0 ? info.width : fallback;
}

static uint32_t app_inputmon_text_scale(void) {
    uint32_t width = app_inputmon_width_or(0);

    if (width >= 1080) {
        return 4;
    }
    if (width >= 720) {
        return 3;
    }
    return 2;
}

static uint32_t app_inputmon_shrink_text_scale(const char *text,
                                               uint32_t scale,
                                               uint32_t max_width) {
    while (scale > 1 && (uint32_t)strlen(text) * scale * 6 > max_width) {
        --scale;
    }
    return scale;
}

static int inputmon_key_index(unsigned int code) {
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

static const char *inputmon_value_name(int value) {
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

void a90_app_inputmon_reset_state(struct a90_app_inputmon_state *monitor) {
    if (monitor == NULL) {
        return;
    }

    a90_input_decoder_init(&monitor->decoder);
    memset(monitor->raw_entries, 0, sizeof(monitor->raw_entries));
    memset(monitor->gesture_title, 0, sizeof(monitor->gesture_title));
    memset(monitor->gesture_detail, 0, sizeof(monitor->gesture_detail));
    memset(monitor->gesture_mask, 0, sizeof(monitor->gesture_mask));
    memset(monitor->key_down_ms, 0, sizeof(monitor->key_down_ms));
    snprintf(monitor->gesture_title, sizeof(monitor->gesture_title),
             "GESTURE waiting");
    snprintf(monitor->gesture_detail, sizeof(monitor->gesture_detail),
             "double=%ldms long=%ldms",
             A90_INPUT_DOUBLE_CLICK_MS,
             A90_INPUT_LONG_PRESS_MS);
    snprintf(monitor->gesture_mask, sizeof(monitor->gesture_mask), "NONE");
    monitor->gesture_id = A90_INPUT_GESTURE_NONE;
    monitor->gesture_action = A90_INPUT_MENU_ACTION_NONE;
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

static void inputmon_push_raw(struct a90_app_inputmon_state *monitor,
                              const char *serial_line,
                              const char *title,
                              const char *detail,
                              int value,
                              bool serial_echo) {
    size_t slot = monitor->raw_head % A90_INPUTMON_ROWS;

    snprintf(monitor->raw_entries[slot].title,
             sizeof(monitor->raw_entries[slot].title),
             "%s", title);
    snprintf(monitor->raw_entries[slot].detail,
             sizeof(monitor->raw_entries[slot].detail),
             "%s", detail);
    monitor->raw_entries[slot].value = value;
    ++monitor->raw_head;
    if (monitor->raw_count < A90_INPUTMON_ROWS) {
        ++monitor->raw_count;
    }

    a90_logf("inputmonitor", "%s", serial_line);
    if (serial_echo) {
        a90_console_printf("inputmonitor: %s\r\n", serial_line);
    }
}

static void inputmon_emit_gesture(struct a90_app_inputmon_state *monitor,
                                  const struct a90_input_gesture *gesture,
                                  bool serial_echo) {
    char mask_text[64];
    long now_ms = monotonic_millis();
    long gap_ms = monitor->last_gesture_ms > 0 ?
                  now_ms - monitor->last_gesture_ms : -1;

    a90_input_mask_text(gesture->mask, mask_text, sizeof(mask_text));
    ++monitor->gesture_count;
    monitor->gesture_id = gesture->id;
    monitor->gesture_action = a90_input_menu_action_from_gesture(gesture);
    monitor->gesture_clicks = gesture->clicks;
    monitor->gesture_duration_ms = gesture->duration_ms;
    monitor->gesture_gap_ms = gap_ms;
    snprintf(monitor->gesture_mask, sizeof(monitor->gesture_mask),
             "%s", mask_text);
    snprintf(monitor->gesture_title, sizeof(monitor->gesture_title),
             "G%03u %s",
             monitor->gesture_count,
             a90_input_gesture_name(gesture->id));
    snprintf(monitor->gesture_detail, sizeof(monitor->gesture_detail),
             "mask=%s click=%u dur=%ldms gap=%ldms action=%s",
             mask_text,
             gesture->clicks,
             gesture->duration_ms,
             gap_ms,
             a90_input_menu_action_name(monitor->gesture_action));
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

bool a90_app_inputmon_feed_state(struct a90_app_inputmon_state *monitor,
                                 const struct input_event *event,
                                 int source_index,
                                 bool serial_echo,
                                 bool exit_on_all_buttons) {
    struct a90_input_gesture gesture;
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

    if (monitor == NULL || event == NULL || event->type != EV_KEY) {
        return false;
    }

    key_index = inputmon_key_index(event->code);
    name = a90_input_key_name(event->code);
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
             inputmon_value_name(event->value),
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
             inputmon_value_name(event->value),
             gap_ms,
             hold_label);
    inputmon_push_raw(monitor,
                      serial_line,
                      title,
                      detail,
                      event->value,
                      serial_echo);

    if (a90_input_decoder_feed(&monitor->decoder, event, now_ms, &gesture)) {
        inputmon_emit_gesture(monitor, &gesture, serial_echo);
        if (exit_on_all_buttons && gesture.id == A90_INPUT_GESTURE_ALL_BUTTONS) {
            monitor->exit_requested = true;
        }
    }

    if (exit_on_all_buttons &&
        event->value == 1 &&
        (monitor->decoder.down_mask &
         (A90_INPUT_BUTTON_VOLUP | A90_INPUT_BUTTON_VOLDOWN | A90_INPUT_BUTTON_POWER)) ==
        (A90_INPUT_BUTTON_VOLUP | A90_INPUT_BUTTON_VOLDOWN | A90_INPUT_BUTTON_POWER)) {
        long duration_ms = now_ms - monitor->decoder.first_down_ms;

        if (duration_ms < 0) {
            duration_ms = 0;
        }
        a90_input_gesture_set(&gesture,
                              A90_INPUT_GESTURE_ALL_BUTTONS,
                              event->code,
                              A90_INPUT_BUTTON_VOLUP | A90_INPUT_BUTTON_VOLDOWN | A90_INPUT_BUTTON_POWER,
                              1,
                              duration_ms);
        inputmon_emit_gesture(monitor, &gesture, serial_echo);
        monitor->exit_requested = true;
    }

    return monitor->exit_requested;
}

void a90_app_inputmon_tick_state(struct a90_app_inputmon_state *monitor,
                                 bool serial_echo) {
    struct a90_input_gesture gesture;

    if (monitor != NULL &&
        a90_input_decoder_emit_pending_if_due(&monitor->decoder, &gesture)) {
        inputmon_emit_gesture(monitor, &gesture, serial_echo);
    }
}

static const struct a90_app_inputmon_raw_entry *inputmon_raw_entry_at(
        const struct a90_app_inputmon_state *monitor,
        size_t reverse_index) {
    size_t slot;

    if (monitor == NULL ||
        reverse_index >= monitor->raw_count ||
        monitor->raw_head == 0) {
        return NULL;
    }

    slot = (monitor->raw_head + A90_INPUTMON_ROWS - 1 - reverse_index) %
           A90_INPUTMON_ROWS;
    return &monitor->raw_entries[slot];
}

static uint32_t inputmon_value_color(int value) {
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

static const char *inputmon_gesture_class(enum a90_input_gesture_id id) {
    switch (id) {
    case A90_INPUT_GESTURE_VOLUP_CLICK:
    case A90_INPUT_GESTURE_VOLDOWN_CLICK:
    case A90_INPUT_GESTURE_POWER_CLICK:
        return "SINGLE CLICK";
    case A90_INPUT_GESTURE_VOLUP_DOUBLE:
    case A90_INPUT_GESTURE_VOLDOWN_DOUBLE:
    case A90_INPUT_GESTURE_POWER_DOUBLE:
        return "DOUBLE CLICK";
    case A90_INPUT_GESTURE_VOLUP_LONG:
    case A90_INPUT_GESTURE_VOLDOWN_LONG:
    case A90_INPUT_GESTURE_POWER_LONG:
        return "LONG HOLD";
    case A90_INPUT_GESTURE_VOLUP_VOLDOWN:
    case A90_INPUT_GESTURE_VOLUP_POWER:
    case A90_INPUT_GESTURE_VOLDOWN_POWER:
    case A90_INPUT_GESTURE_ALL_BUTTONS:
        return "COMBO INPUT";
    case A90_INPUT_GESTURE_NONE:
        return "WAITING";
    default:
        return "UNKNOWN";
    }
}

static uint32_t inputmon_gesture_color(enum a90_input_gesture_id id) {
    switch (id) {
    case A90_INPUT_GESTURE_VOLUP_CLICK:
    case A90_INPUT_GESTURE_VOLDOWN_CLICK:
    case A90_INPUT_GESTURE_POWER_CLICK:
        return 0x88ee88;
    case A90_INPUT_GESTURE_VOLUP_DOUBLE:
    case A90_INPUT_GESTURE_VOLDOWN_DOUBLE:
    case A90_INPUT_GESTURE_POWER_DOUBLE:
        return 0xffcc33;
    case A90_INPUT_GESTURE_VOLUP_LONG:
    case A90_INPUT_GESTURE_VOLDOWN_LONG:
    case A90_INPUT_GESTURE_POWER_LONG:
        return 0xff8844;
    case A90_INPUT_GESTURE_VOLUP_VOLDOWN:
    case A90_INPUT_GESTURE_VOLUP_POWER:
    case A90_INPUT_GESTURE_VOLDOWN_POWER:
    case A90_INPUT_GESTURE_ALL_BUTTONS:
        return 0x66ddff;
    case A90_INPUT_GESTURE_NONE:
        return 0x808080;
    default:
        return 0xff7777;
    }
}

static uint32_t inputmon_action_color(enum a90_input_menu_action action) {
    switch (action) {
    case A90_INPUT_MENU_ACTION_SELECT:
        return 0x88ee88;
    case A90_INPUT_MENU_ACTION_BACK:
    case A90_INPUT_MENU_ACTION_HIDE:
        return 0xffcc33;
    case A90_INPUT_MENU_ACTION_PAGE_PREV:
    case A90_INPUT_MENU_ACTION_PAGE_NEXT:
    case A90_INPUT_MENU_ACTION_PREV:
    case A90_INPUT_MENU_ACTION_NEXT:
        return 0x66ddff;
    case A90_INPUT_MENU_ACTION_RESERVED:
        return 0xff7777;
    default:
        return 0xffffff;
    }
}

int a90_app_inputmon_draw_state(const struct a90_app_inputmon_state *monitor) {
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

    if (monitor == NULL) {
        return -EINVAL;
    }
    if (a90_kms_begin_frame(0x050505) < 0) {
        return negative_errno_or(ENODEV);
    }

    scale = app_inputmon_text_scale();
    if (scale > 3) {
        scale = 3;
    }
    title_scale = scale + 1;
    big_scale = scale * 3;
    left = a90_kms_framebuffer()->width / 18;
    if (left < scale * 4) {
        left = scale * 4;
    }
    top = a90_kms_framebuffer()->height / 12;
    content_width = a90_kms_framebuffer()->width - (left * 2);
    line_height = scale * 10;
    row_gap = scale * 3;
    row_height = line_height * 2 + row_gap;
    panel_height = line_height * 9;
    card_height = panel_height + line_height +
                  (uint32_t)A90_INPUTMON_ROWS * row_height +
                  scale * 4;

    snprintf(summary, sizeof(summary), "RAW %u  GESTURE %u",
             monitor->event_count,
             monitor->gesture_count);
    snprintf(timing, sizeof(timing), "DOWN/UP GAP HOLD / DBL %ld LONG %ld",
             A90_INPUT_DOUBLE_CLICK_MS,
             A90_INPUT_LONG_PRESS_MS);
    snprintf(buttons_line, sizeof(buttons_line), "BUTTONS  %s",
             monitor->gesture_mask);
    snprintf(action_line, sizeof(action_line), "ACTION   %s",
             a90_input_menu_action_name(monitor->gesture_action));
    snprintf(metric_line, sizeof(metric_line),
             "click=%u  duration=%ldms  gap=%ldms",
             monitor->gesture_clicks,
             monitor->gesture_duration_ms,
             monitor->gesture_gap_ms);

    a90_draw_text(a90_kms_framebuffer(), left, top, "TOOLS / INPUT MONITOR", 0xffcc33,
                  app_inputmon_shrink_text_scale("TOOLS / INPUT MONITOR",
                                                 title_scale,
                                                 content_width));
    top += line_height;
    a90_draw_text(a90_kms_framebuffer(), left, top, summary, 0x88ee88,
                  app_inputmon_shrink_text_scale(summary, scale, content_width));
    top += line_height;
    a90_draw_text(a90_kms_framebuffer(), left, top, timing, 0xdddddd,
                  app_inputmon_shrink_text_scale(timing, scale, content_width));
    top += line_height + scale * 2;

    a90_draw_rect(a90_kms_framebuffer(),
                  left - scale,
                  top - scale,
                  content_width,
                  card_height,
                  0x202020);

    panel_top = top;
    half_width = (content_width - scale * 4) / 2;
    class_color = inputmon_gesture_color(monitor->gesture_id);
    action_color = inputmon_action_color(monitor->gesture_action);

    a90_draw_rect(a90_kms_framebuffer(),
                  left,
                  panel_top,
                  content_width - scale * 2,
                  panel_height,
                  0x101820);
    a90_draw_rect(a90_kms_framebuffer(),
                  left,
                  panel_top,
                  scale * 3,
                  panel_height,
                  class_color);

    a90_draw_text(a90_kms_framebuffer(),
                  left + scale * 5,
                  panel_top + scale * 4,
                  "DECODED INPUT LAYER",
                  0x909090,
                  scale);
    a90_draw_text(a90_kms_framebuffer(),
                  left + scale * 5,
                  panel_top + line_height + scale * 4,
                  inputmon_gesture_class(monitor->gesture_id),
                  class_color,
                  app_inputmon_shrink_text_scale(inputmon_gesture_class(monitor->gesture_id),
                                                 big_scale,
                                                 content_width - scale * 10));
    a90_draw_text(a90_kms_framebuffer(),
                  left + scale * 5,
                  panel_top + line_height * 4,
                  monitor->gesture_title,
                  0xffffff,
                  app_inputmon_shrink_text_scale(monitor->gesture_title,
                                                 scale,
                                                 content_width - scale * 10));

    panel_mid = panel_top + line_height * 5 + scale * 4;
    a90_draw_rect(a90_kms_framebuffer(),
                  left + scale * 5,
                  panel_mid,
                  half_width - scale * 2,
                  line_height * 2,
                  0x182030);
    a90_draw_rect(a90_kms_framebuffer(),
                  left + half_width + scale * 3,
                  panel_mid,
                  half_width - scale * 2,
                  line_height * 2,
                  0x182030);
    a90_draw_text(a90_kms_framebuffer(),
                  left + scale * 7,
                  panel_mid + scale * 3,
                  buttons_line,
                  0x66ddff,
                  app_inputmon_shrink_text_scale(buttons_line,
                                                 scale,
                                                 half_width - scale * 6));
    a90_draw_text(a90_kms_framebuffer(),
                  left + half_width + scale * 5,
                  panel_mid + scale * 3,
                  action_line,
                  action_color,
                  app_inputmon_shrink_text_scale(action_line,
                                                 scale,
                                                 half_width - scale * 6));
    a90_draw_text(a90_kms_framebuffer(),
                  left + scale * 5,
                  panel_top + panel_height - line_height - scale * 3,
                  metric_line,
                  0xdddddd,
                  app_inputmon_shrink_text_scale(metric_line,
                                                 scale,
                                                 content_width - scale * 10));

    top = panel_top + panel_height + line_height;

    for (index = 0; index < A90_INPUTMON_ROWS; ++index) {
        const struct a90_app_inputmon_raw_entry *entry =
            inputmon_raw_entry_at(monitor, index);
        uint32_t row_y = top + (uint32_t)index * row_height;
        uint32_t title_color;

        if (entry == NULL) {
            continue;
        }

        title_color = inputmon_value_color(entry->value);
        a90_draw_rect(a90_kms_framebuffer(),
                      left,
                      row_y - scale,
                      content_width - scale * 2,
                      line_height * 2 + scale,
                      index == 0 ? 0x283030 : 0x181818);
        a90_draw_text(a90_kms_framebuffer(),
                      left + scale * 2,
                      row_y,
                      entry->title,
                      title_color,
                      app_inputmon_shrink_text_scale(entry->title,
                                                     scale,
                                                     content_width - scale * 4));
        a90_draw_text(a90_kms_framebuffer(),
                      left + scale * 5,
                      row_y + line_height,
                      entry->detail,
                      index == 0 ? 0xffffff : 0xa8a8a8,
                      app_inputmon_shrink_text_scale(entry->detail,
                                                     scale,
                                                     content_width - scale * 7));
    }

    a90_draw_text(a90_kms_framebuffer(),
                  left,
                  a90_kms_framebuffer()->height - scale * 12,
                  "ALL BUTTONS EXIT / BRIDGE hide",
                  0xffffff,
                  app_inputmon_shrink_text_scale("ALL BUTTONS EXIT / BRIDGE hide",
                                                 scale,
                                                 content_width));

    if (a90_kms_present("inputmonitor", false) < 0) {
        return negative_errno_or(EIO);
    }
    return 0;
}

int a90_app_inputmon_draw_layout(void) {
    const char *lines[] = {
        "VOL+  previous / page previous",
        "VOL-  next / page next",
        "POWER select / single action",
        "LONG POWER back / hide app",
        "VOL+ + VOL- page previous",
        "VOL+ + POWER page next",
        "VOL- + POWER hide",
        "ALL BUTTONS exit monitor",
    };
    const char *footer = "USE waitkey / waitgesture / inputmonitor FOR LIVE TEST";
    uint32_t scale;
    uint32_t title_scale;
    uint32_t left;
    uint32_t top;
    uint32_t content_width;
    uint32_t line_height;
    size_t index;

    if (a90_kms_begin_frame(0x050505) < 0) {
        return negative_errno_or(ENODEV);
    }

    scale = app_inputmon_text_scale();
    if (scale > 3) {
        scale = 3;
    }
    title_scale = scale + 1;
    left = a90_kms_framebuffer()->width / 18;
    if (left < scale * 4) {
        left = scale * 4;
    }
    top = a90_kms_framebuffer()->height / 12;
    content_width = a90_kms_framebuffer()->width - (left * 2);
    line_height = scale * 11;

    a90_draw_text(a90_kms_framebuffer(),
                  left,
                  top,
                  "TOOLS / INPUT LAYOUT",
                  0xffcc33,
                  app_inputmon_shrink_text_scale("TOOLS / INPUT LAYOUT",
                                                 title_scale,
                                                 content_width));
    top += line_height + scale * 2;
    a90_draw_rect(a90_kms_framebuffer(),
                  left - scale,
                  top - scale,
                  content_width,
                  line_height * ((uint32_t)A90_APP_INPUTMON_COUNT(lines) + 1),
                  0x202020);

    for (index = 0; index < A90_APP_INPUTMON_COUNT(lines); ++index) {
        a90_draw_text(a90_kms_framebuffer(),
                      left,
                      top + (uint32_t)index * line_height,
                      lines[index],
                      index < 3 ? 0x88ee88 : 0xffffff,
                      app_inputmon_shrink_text_scale(lines[index],
                                                     scale,
                                                     content_width - scale * 2));
    }

    a90_draw_text(a90_kms_framebuffer(),
                  left,
                  a90_kms_framebuffer()->height - scale * 12,
                  footer,
                  0xffffff,
                  app_inputmon_shrink_text_scale(footer, scale, content_width));

    if (a90_kms_present("inputlayout", true) < 0) {
        return negative_errno_or(EIO);
    }
    return 0;
}

static void inputmon_foreground_prepare(
        const struct a90_app_inputmon_foreground_hooks *hooks) {
    if (hooks != NULL && hooks->prepare != NULL) {
        hooks->prepare(hooks->userdata);
    }
}

static void inputmon_foreground_restore(
        const struct a90_app_inputmon_foreground_hooks *hooks,
        bool restore_hud) {
    if (hooks != NULL && hooks->restore != NULL) {
        hooks->restore(hooks->userdata, restore_hud);
    }
}

static int inputmon_foreground_close_restore(
        struct a90_input_context *ctx,
        const struct a90_app_inputmon_foreground_hooks *hooks,
        bool restore_hud,
        int rc) {
    if (ctx != NULL) {
        a90_input_close(ctx);
    }
    inputmon_foreground_restore(hooks, restore_hud);
    return rc;
}

int a90_app_inputmon_run_foreground(
        char **argv,
        int argc,
        const struct a90_app_inputmon_foreground_hooks *hooks) {
    struct a90_app_inputmon_state monitor;
    struct a90_input_context ctx;
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

    inputmon_foreground_prepare(hooks);
    a90_app_inputmon_reset_state(&monitor);

    if (a90_input_open(&ctx, "inputmonitor") < 0) {
        inputmon_foreground_restore(hooks, true);
        return negative_errno_or(ENOENT);
    }

    a90_console_printf("inputmonitor: raw DOWN/UP/REPEAT + gesture decode\r\n");
    a90_console_printf("inputmonitor: events=%d, 0 means until all-buttons/q/Ctrl-C\r\n", target);
    a90_console_printf("inputmonitor: all-buttons exits only in events=0 mode\r\n");

    draw_rc = a90_app_inputmon_draw_state(&monitor);
    if (draw_rc < 0) {
        return inputmon_foreground_close_restore(&ctx, hooks, true, draw_rc);
    }

    while (target == 0 || seen < target) {
        struct pollfd fds[3];
        int timeout_ms;
        int poll_rc;
        int index;

        a90_app_inputmon_tick_state(&monitor, true);
        a90_app_inputmon_draw_state(&monitor);

        fds[0].fd = ctx.fd0;
        fds[0].events = POLLIN;
        fds[0].revents = 0;
        fds[1].fd = ctx.fd3;
        fds[1].events = POLLIN;
        fds[1].revents = 0;
        fds[2].fd = STDIN_FILENO;
        fds[2].events = POLLIN;
        fds[2].revents = 0;

        timeout_ms = a90_input_decoder_timeout_ms(&monitor.decoder);
        poll_rc = poll(fds, 3, timeout_ms);
        if (poll_rc < 0) {
            int saved_errno = errno;

            if (errno == EINTR) {
                continue;
            }
            a90_console_printf("inputmonitor: poll: %s\r\n", strerror(saved_errno));
            return inputmon_foreground_close_restore(
                &ctx,
                hooks,
                true,
                -saved_errno);
        }

        if (poll_rc == 0) {
            continue;
        }

        if ((fds[2].revents & POLLIN) != 0) {
            enum a90_cancel_kind cancel = a90_console_read_cancel_event();

            if (cancel != CANCEL_NONE) {
                return inputmon_foreground_close_restore(
                    &ctx,
                    hooks,
                    true,
                    a90_console_cancelled("inputmonitor", cancel));
            }
        }

        for (index = 0; index < 2; ++index) {
            if ((fds[index].revents & POLLIN) != 0) {
                struct input_event event;
                ssize_t rd;

                while ((rd = read(fds[index].fd, &event, sizeof(event))) ==
                       (ssize_t)sizeof(event)) {
                    unsigned int before_count = monitor.event_count;

                    if (a90_app_inputmon_feed_state(&monitor,
                                                    &event,
                                                    index,
                                                    true,
                                                    target == 0)) {
                        a90_app_inputmon_draw_state(&monitor);
                        return inputmon_foreground_close_restore(
                            &ctx,
                            hooks,
                            true,
                            0);
                    }
                    if (monitor.event_count > before_count) {
                        ++seen;
                    }
                    a90_app_inputmon_draw_state(&monitor);
                    if (target > 0 && seen >= target) {
                        break;
                    }
                }

                if (rd < 0 && errno != EAGAIN && errno != EWOULDBLOCK) {
                    int saved_errno = errno;

                    a90_console_printf("inputmonitor: read: %s\r\n",
                                       strerror(saved_errno));
                    return inputmon_foreground_close_restore(
                        &ctx,
                        hooks,
                        true,
                        -saved_errno);
                }
            }
            if ((fds[index].revents & (POLLERR | POLLHUP | POLLNVAL)) != 0) {
                a90_console_printf("inputmonitor: poll error revents=0x%x\r\n",
                                   fds[index].revents);
                return inputmon_foreground_close_restore(
                    &ctx,
                    hooks,
                    true,
                    -EIO);
            }
        }
    }

    a90_app_inputmon_tick_state(&monitor, true);
    a90_app_inputmon_draw_state(&monitor);
    return inputmon_foreground_close_restore(&ctx, hooks, true, 0);
}
