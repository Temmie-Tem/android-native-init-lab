#include "a90_input.h"

#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <poll.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <unistd.h>

#include "a90_console.h"
#include "a90_util.h"

static int a90_input_parse_dev_numbers(const char *dev_info,
                                       unsigned int *major_num,
                                       unsigned int *minor_num) {
    if (sscanf(dev_info, "%u:%u", major_num, minor_num) != 2) {
        errno = EINVAL;
        return -1;
    }
    return 0;
}

static int a90_input_ensure_char_node(const char *path,
                                      unsigned int major_num,
                                      unsigned int minor_num) {
    if (mknod(path, S_IFCHR | 0600, makedev(major_num, minor_num)) < 0 &&
        errno != EEXIST) {
        return -1;
    }
    return 0;
}

static bool a90_input_is_strict_event_name(const char *event_name) {
    size_t index;

    if (strncmp(event_name, "event", 5) != 0 ||
        event_name[5] < '0' ||
        event_name[5] > '9') {
        return false;
    }
    for (index = 6; event_name[index] != '\0'; ++index) {
        if (event_name[index] < '0' || event_name[index] > '9') {
            return false;
        }
    }
    return true;
}

static int a90_input_event_path(const char *event_name, char *out, size_t out_size) {
    char dev_info_path[PATH_MAX];
    char dev_info[64];
    unsigned int major_num;
    unsigned int minor_num;

    if (!a90_input_is_strict_event_name(event_name)) {
        errno = EINVAL;
        return -1;
    }

    if (snprintf(dev_info_path, sizeof(dev_info_path),
                 "/sys/class/input/%s/dev", event_name) >= (int)sizeof(dev_info_path)) {
        errno = ENAMETOOLONG;
        return -1;
    }
    if (read_trimmed_text_file(dev_info_path, dev_info, sizeof(dev_info)) < 0) {
        return -1;
    }
    if (a90_input_parse_dev_numbers(dev_info, &major_num, &minor_num) < 0) {
        return -1;
    }
    if (ensure_dir("/dev/input", 0755) < 0) {
        return -1;
    }
    if (snprintf(out, out_size, "/dev/input/%s", event_name) >= (int)out_size) {
        errno = ENAMETOOLONG;
        return -1;
    }
    return a90_input_ensure_char_node(out, major_num, minor_num);
}

const char *a90_input_key_name(unsigned int code) {
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

unsigned int a90_input_button_mask_from_key(unsigned int code) {
    switch (code) {
    case KEY_VOLUMEUP:
        return A90_INPUT_BUTTON_VOLUP;
    case KEY_VOLUMEDOWN:
        return A90_INPUT_BUTTON_VOLDOWN;
    case KEY_POWER:
        return A90_INPUT_BUTTON_POWER;
    default:
        return 0;
    }
}

static unsigned int a90_input_button_count(unsigned int mask) {
    unsigned int count = 0;

    if ((mask & A90_INPUT_BUTTON_VOLUP) != 0) {
        ++count;
    }
    if ((mask & A90_INPUT_BUTTON_VOLDOWN) != 0) {
        ++count;
    }
    if ((mask & A90_INPUT_BUTTON_POWER) != 0) {
        ++count;
    }
    return count;
}

void a90_input_mask_text(unsigned int mask, char *buf, size_t buf_size) {
    size_t used = 0;

    if (buf_size == 0) {
        return;
    }
    buf[0] = '\0';
    if ((mask & A90_INPUT_BUTTON_VOLUP) != 0) {
        used += snprintf(buf + used, used < buf_size ? buf_size - used : 0,
                         "%sVOLUP", used > 0 ? "+" : "");
    }
    if ((mask & A90_INPUT_BUTTON_VOLDOWN) != 0) {
        used += snprintf(buf + used, used < buf_size ? buf_size - used : 0,
                         "%sVOLDOWN", used > 0 ? "+" : "");
    }
    if ((mask & A90_INPUT_BUTTON_POWER) != 0) {
        used += snprintf(buf + used, used < buf_size ? buf_size - used : 0,
                         "%sPOWER", used > 0 ? "+" : "");
    }
    if (used == 0) {
        snprintf(buf, buf_size, "NONE");
    }
}

const char *a90_input_gesture_name(enum a90_input_gesture_id id) {
    switch (id) {
    case A90_INPUT_GESTURE_VOLUP_CLICK:
        return "VOLUP_CLICK";
    case A90_INPUT_GESTURE_VOLDOWN_CLICK:
        return "VOLDOWN_CLICK";
    case A90_INPUT_GESTURE_POWER_CLICK:
        return "POWER_CLICK";
    case A90_INPUT_GESTURE_VOLUP_DOUBLE:
        return "VOLUP_DOUBLE";
    case A90_INPUT_GESTURE_VOLDOWN_DOUBLE:
        return "VOLDOWN_DOUBLE";
    case A90_INPUT_GESTURE_POWER_DOUBLE:
        return "POWER_DOUBLE";
    case A90_INPUT_GESTURE_VOLUP_LONG:
        return "VOLUP_LONG";
    case A90_INPUT_GESTURE_VOLDOWN_LONG:
        return "VOLDOWN_LONG";
    case A90_INPUT_GESTURE_POWER_LONG:
        return "POWER_LONG";
    case A90_INPUT_GESTURE_VOLUP_VOLDOWN:
        return "VOLUP+VOLDOWN";
    case A90_INPUT_GESTURE_VOLUP_POWER:
        return "VOLUP+POWER";
    case A90_INPUT_GESTURE_VOLDOWN_POWER:
        return "VOLDOWN+POWER";
    case A90_INPUT_GESTURE_ALL_BUTTONS:
        return "VOLUP+VOLDOWN+POWER";
    default:
        return "NONE";
    }
}

static enum a90_input_gesture_id a90_input_single_gesture(unsigned int code,
                                                          unsigned int clicks,
                                                          long duration_ms) {
    if (duration_ms >= A90_INPUT_LONG_PRESS_MS) {
        switch (code) {
        case KEY_VOLUMEUP:
            return A90_INPUT_GESTURE_VOLUP_LONG;
        case KEY_VOLUMEDOWN:
            return A90_INPUT_GESTURE_VOLDOWN_LONG;
        case KEY_POWER:
            return A90_INPUT_GESTURE_POWER_LONG;
        default:
            return A90_INPUT_GESTURE_NONE;
        }
    }
    if (clicks >= 2) {
        switch (code) {
        case KEY_VOLUMEUP:
            return A90_INPUT_GESTURE_VOLUP_DOUBLE;
        case KEY_VOLUMEDOWN:
            return A90_INPUT_GESTURE_VOLDOWN_DOUBLE;
        case KEY_POWER:
            return A90_INPUT_GESTURE_POWER_DOUBLE;
        default:
            return A90_INPUT_GESTURE_NONE;
        }
    }
    switch (code) {
    case KEY_VOLUMEUP:
        return A90_INPUT_GESTURE_VOLUP_CLICK;
    case KEY_VOLUMEDOWN:
        return A90_INPUT_GESTURE_VOLDOWN_CLICK;
    case KEY_POWER:
        return A90_INPUT_GESTURE_POWER_CLICK;
    default:
        return A90_INPUT_GESTURE_NONE;
    }
}

static enum a90_input_gesture_id a90_input_combo_gesture(unsigned int mask) {
    switch (mask & (A90_INPUT_BUTTON_VOLUP |
                    A90_INPUT_BUTTON_VOLDOWN |
                    A90_INPUT_BUTTON_POWER)) {
    case A90_INPUT_BUTTON_VOLUP | A90_INPUT_BUTTON_VOLDOWN:
        return A90_INPUT_GESTURE_VOLUP_VOLDOWN;
    case A90_INPUT_BUTTON_VOLUP | A90_INPUT_BUTTON_POWER:
        return A90_INPUT_GESTURE_VOLUP_POWER;
    case A90_INPUT_BUTTON_VOLDOWN | A90_INPUT_BUTTON_POWER:
        return A90_INPUT_GESTURE_VOLDOWN_POWER;
    case A90_INPUT_BUTTON_VOLUP | A90_INPUT_BUTTON_VOLDOWN | A90_INPUT_BUTTON_POWER:
        return A90_INPUT_GESTURE_ALL_BUTTONS;
    default:
        return A90_INPUT_GESTURE_NONE;
    }
}

void a90_input_gesture_set(struct a90_input_gesture *gesture,
                           enum a90_input_gesture_id id,
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

enum a90_input_menu_action a90_input_menu_action_from_gesture(
        const struct a90_input_gesture *gesture) {
    switch (gesture->id) {
    case A90_INPUT_GESTURE_VOLUP_CLICK:
        return A90_INPUT_MENU_ACTION_PREV;
    case A90_INPUT_GESTURE_VOLDOWN_CLICK:
        return A90_INPUT_MENU_ACTION_NEXT;
    case A90_INPUT_GESTURE_POWER_CLICK:
        return A90_INPUT_MENU_ACTION_SELECT;
    case A90_INPUT_GESTURE_VOLUP_DOUBLE:
    case A90_INPUT_GESTURE_VOLUP_LONG:
        return A90_INPUT_MENU_ACTION_PAGE_PREV;
    case A90_INPUT_GESTURE_VOLDOWN_DOUBLE:
    case A90_INPUT_GESTURE_VOLDOWN_LONG:
        return A90_INPUT_MENU_ACTION_PAGE_NEXT;
    case A90_INPUT_GESTURE_POWER_DOUBLE:
    case A90_INPUT_GESTURE_VOLUP_VOLDOWN:
        return A90_INPUT_MENU_ACTION_BACK;
    case A90_INPUT_GESTURE_ALL_BUTTONS:
        return A90_INPUT_MENU_ACTION_HIDE;
    case A90_INPUT_GESTURE_VOLUP_POWER:
        return A90_INPUT_MENU_ACTION_STATUS;
    case A90_INPUT_GESTURE_VOLDOWN_POWER:
        return A90_INPUT_MENU_ACTION_LOG;
    case A90_INPUT_GESTURE_POWER_LONG:
        return A90_INPUT_MENU_ACTION_RESERVED;
    default:
        return A90_INPUT_MENU_ACTION_NONE;
    }
}

const char *a90_input_menu_action_name(enum a90_input_menu_action action) {
    switch (action) {
    case A90_INPUT_MENU_ACTION_PREV:
        return "PREVIOUS";
    case A90_INPUT_MENU_ACTION_NEXT:
        return "NEXT";
    case A90_INPUT_MENU_ACTION_SELECT:
        return "SELECT";
    case A90_INPUT_MENU_ACTION_BACK:
        return "BACK";
    case A90_INPUT_MENU_ACTION_HIDE:
        return "HIDE/EXIT";
    case A90_INPUT_MENU_ACTION_PAGE_PREV:
        return "PAGE UP";
    case A90_INPUT_MENU_ACTION_PAGE_NEXT:
        return "PAGE DOWN";
    case A90_INPUT_MENU_ACTION_STATUS:
        return "STATUS";
    case A90_INPUT_MENU_ACTION_LOG:
        return "LOG";
    case A90_INPUT_MENU_ACTION_RESERVED:
        return "RESERVED";
    default:
        return "NONE";
    }
}

int a90_input_open(struct a90_input_context *ctx, const char *tag) {
    char event0_path[PATH_MAX];
    char event3_path[PATH_MAX];

    ctx->fd0 = -1;
    ctx->fd3 = -1;

    if (a90_input_event_path("event0", event0_path, sizeof(event0_path)) < 0 ||
        a90_input_event_path("event3", event3_path, sizeof(event3_path)) < 0) {
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

void a90_input_close(struct a90_input_context *ctx) {
    if (ctx->fd0 >= 0) {
        close(ctx->fd0);
        ctx->fd0 = -1;
    }
    if (ctx->fd3 >= 0) {
        close(ctx->fd3);
        ctx->fd3 = -1;
    }
}

int a90_input_poll_event(struct a90_input_context *ctx,
                         const char *tag,
                         int timeout_ms,
                         bool allow_console_cancel,
                         struct input_event *event_out,
                         int *source_index_out) {
    struct pollfd fds[3];
    int nfds = allow_console_cancel ? 3 : 2;

    fds[0].fd = ctx->fd0;
    fds[0].events = POLLIN;
    fds[0].revents = 0;
    fds[1].fd = ctx->fd3;
    fds[1].events = POLLIN;
    fds[1].revents = 0;
    fds[2].fd = STDIN_FILENO;
    fds[2].events = POLLIN;
    fds[2].revents = 0;

    while (1) {
        int poll_rc = poll(fds, nfds, timeout_ms);
        int index;

        if (poll_rc < 0) {
            int saved_errno = errno;

            if (saved_errno == EINTR) {
                continue;
            }
            a90_console_printf("%s: poll: %s\r\n", tag, strerror(saved_errno));
            return -saved_errno;
        }
        if (poll_rc == 0) {
            return 0;
        }
        if (allow_console_cancel && (fds[2].revents & POLLIN) != 0) {
            enum a90_cancel_kind cancel = a90_console_read_cancel_event();

            if (cancel != CANCEL_NONE) {
                return a90_console_cancelled(tag, cancel);
            }
        }

        for (index = 0; index < 2; ++index) {
            if ((fds[index].revents & POLLIN) != 0) {
                ssize_t rd = read(fds[index].fd, event_out, sizeof(*event_out));

                if (rd == (ssize_t)sizeof(*event_out)) {
                    if (source_index_out != NULL) {
                        *source_index_out = index;
                    }
                    return 1;
                }
                if (rd < 0 && (errno == EAGAIN || errno == EWOULDBLOCK)) {
                    continue;
                }
                if (rd < 0) {
                    int saved_errno = errno;

                    a90_console_printf("%s: read: %s\r\n", tag, strerror(saved_errno));
                    return -saved_errno;
                }
                a90_console_printf("%s: short read %ld\r\n", tag, (long)rd);
                return -EIO;
            }
            if ((fds[index].revents & (POLLERR | POLLHUP | POLLNVAL)) != 0) {
                a90_console_printf("%s: poll error revents=0x%x\r\n", tag, fds[index].revents);
                return -EIO;
            }
        }
    }
}

int a90_input_wait_key_press(struct a90_input_context *ctx,
                             const char *tag,
                             unsigned int *code_out) {
    while (1) {
        struct input_event event;
        int poll_rc = a90_input_poll_event(ctx, tag, -1, true, &event, NULL);

        if (poll_rc < 0) {
            return poll_rc;
        }
        if (poll_rc == 0) {
            continue;
        }
        if (event.type == EV_KEY && event.value == 1) {
            *code_out = event.code;
            return 0;
        }
    }
}

void a90_input_decoder_init(struct a90_input_decoder *decoder) {
    memset(decoder, 0, sizeof(*decoder));
}

int a90_input_decoder_timeout_ms(const struct a90_input_decoder *decoder) {
    long elapsed_ms;
    long remaining_ms;

    if (!decoder->waiting_second) {
        return -1;
    }

    elapsed_ms = monotonic_millis() - decoder->pending_up_ms;
    if (elapsed_ms >= A90_INPUT_DOUBLE_CLICK_MS) {
        return 0;
    }

    remaining_ms = A90_INPUT_DOUBLE_CLICK_MS - elapsed_ms;
    if (remaining_ms > INT_MAX) {
        return INT_MAX;
    }
    return (int)remaining_ms;
}

bool a90_input_decoder_emit_pending_if_due(struct a90_input_decoder *decoder,
                                           struct a90_input_gesture *gesture) {
    long elapsed_ms;

    if (!decoder->waiting_second) {
        return false;
    }

    elapsed_ms = monotonic_millis() - decoder->pending_up_ms;
    if (elapsed_ms < A90_INPUT_DOUBLE_CLICK_MS) {
        return false;
    }

    a90_input_gesture_set(gesture,
                          a90_input_single_gesture(decoder->pending_code,
                                                   1,
                                                   decoder->pending_duration_ms),
                          decoder->pending_code,
                          decoder->pending_mask,
                          1,
                          decoder->pending_duration_ms);
    decoder->waiting_second = false;
    return true;
}

bool a90_input_decoder_feed(struct a90_input_decoder *decoder,
                            const struct input_event *event,
                            long now_ms,
                            struct a90_input_gesture *gesture) {
    unsigned int mask;

    if (event->type != EV_KEY || event->value == 2) {
        return false;
    }

    mask = a90_input_button_mask_from_key(event->code);
    if (mask == 0) {
        return false;
    }

    if (event->value == 1) {
        if (decoder->waiting_second) {
            if (mask == decoder->pending_mask &&
                decoder->down_mask == 0 &&
                now_ms - decoder->pending_up_ms <= A90_INPUT_DOUBLE_CLICK_MS) {
                decoder->waiting_second = false;
                decoder->second_click = true;
                decoder->down_mask = mask;
                decoder->pressed_mask = mask;
                decoder->primary_code = event->code;
                decoder->primary_mask = mask;
                decoder->first_down_ms = now_ms;
            } else {
                a90_input_gesture_set(gesture,
                                      a90_input_single_gesture(decoder->pending_code,
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
            unsigned int count = a90_input_button_count(decoder->pressed_mask);

            if (count > 1) {
                a90_input_gesture_set(gesture,
                                      a90_input_combo_gesture(decoder->pressed_mask),
                                      decoder->primary_code,
                                      decoder->pressed_mask,
                                      1,
                                      duration_ms);
                decoder->pressed_mask = 0;
                return true;
            }
            if (decoder->second_click) {
                a90_input_gesture_set(gesture,
                                      a90_input_single_gesture(decoder->primary_code,
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
            if (duration_ms >= A90_INPUT_LONG_PRESS_MS) {
                a90_input_gesture_set(gesture,
                                      a90_input_single_gesture(decoder->primary_code,
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

int a90_input_wait_gesture(struct a90_input_context *ctx,
                           const char *tag,
                           struct a90_input_gesture *gesture) {
    struct a90_input_decoder decoder;

    a90_input_decoder_init(&decoder);

    while (1) {
        struct input_event event;
        int timeout_ms;
        int poll_rc;

        if (a90_input_decoder_emit_pending_if_due(&decoder, gesture)) {
            return 0;
        }
        timeout_ms = a90_input_decoder_timeout_ms(&decoder);

        poll_rc = a90_input_poll_event(ctx, tag, timeout_ms, true, &event, NULL);
        if (poll_rc < 0) {
            return poll_rc;
        }
        if (poll_rc == 0) {
            continue;
        }
        if (a90_input_decoder_feed(&decoder, &event, monotonic_millis(), gesture)) {
            return 0;
        }
    }
}

void a90_input_print_layout(void) {
    a90_console_printf("inputlayout: single click\r\n");
    a90_console_printf("  VOLUP    -> previous item\r\n");
    a90_console_printf("  VOLDOWN  -> next item\r\n");
    a90_console_printf("  POWER    -> select\r\n");
    a90_console_printf("inputlayout: double click / long press\r\n");
    a90_console_printf("  VOLUP    -> page previous (%d items)\r\n", A90_INPUT_PAGE_STEP);
    a90_console_printf("  VOLDOWN  -> page next (%d items)\r\n", A90_INPUT_PAGE_STEP);
    a90_console_printf("  POWER x2 -> back\r\n");
    a90_console_printf("  POWER long -> reserved/ignored for safety\r\n");
    a90_console_printf("inputlayout: combos\r\n");
    a90_console_printf("  VOLUP+VOLDOWN -> back\r\n");
    a90_console_printf("  VOLUP+POWER   -> status shortcut\r\n");
    a90_console_printf("  VOLDOWN+POWER -> log shortcut\r\n");
    a90_console_printf("  all buttons   -> hide/exit menu\r\n");
    a90_console_printf("timing: double=%ldms long=%ldms\r\n",
            A90_INPUT_DOUBLE_CLICK_MS,
            A90_INPUT_LONG_PRESS_MS);
}
