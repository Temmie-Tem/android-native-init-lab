#include "a90_input_cmd.h"

#include <errno.h>
#include <stdio.h>

#include "a90_app_inputmon.h"
#include "a90_console.h"
#include "a90_input.h"
#include "a90_util.h"

int a90_input_cmd_waitkey(char **argv, int argc) {
    struct a90_input_context ctx;
    int target = 1;
    int seen = 0;

    if (argc >= 2 && sscanf(argv[1], "%d", &target) != 1) {
        a90_console_printf("usage: waitkey [count]\r\n");
        return -EINVAL;
    }
    if (target <= 0) {
        target = 1;
    }

    if (a90_input_open(&ctx, "waitkey") < 0) {
        return negative_errno_or(ENOENT);
    }

    a90_console_printf("waitkey: waiting for %d key press(es), q/Ctrl-C cancels\r\n", target);

    while (seen < target) {
        unsigned int code = 0;
        const char *name;
        int wait_rc = a90_input_wait_key_press(&ctx, "waitkey", &code);

        if (wait_rc < 0) {
            a90_input_close(&ctx);
            return wait_rc;
        }

        name = a90_input_key_name(code);
        if (name != NULL) {
            a90_console_printf("key %d: %s (0x%04x)\r\n", seen, name, code);
        } else {
            a90_console_printf("key %d: code=0x%04x\r\n", seen, code);
        }
        ++seen;
    }

    a90_input_close(&ctx);
    return 0;
}

int a90_input_cmd_inputlayout(char **argv, int argc) {
    (void)argv;
    (void)argc;
    a90_input_print_layout();
    return a90_app_inputmon_draw_layout();
}

int a90_input_cmd_waitgesture(char **argv, int argc) {
    struct a90_input_context ctx;
    int target = 1;
    int seen = 0;

    if (argc >= 2 && sscanf(argv[1], "%d", &target) != 1) {
        a90_console_printf("usage: waitgesture [count]\r\n");
        return -EINVAL;
    }
    if (target <= 0) {
        target = 1;
    }

    if (a90_input_open(&ctx, "waitgesture") < 0) {
        return negative_errno_or(ENOENT);
    }

    a90_console_printf("waitgesture: waiting for %d gesture(s), q/Ctrl-C cancels\r\n", target);
    a90_console_printf("waitgesture: double=%ldms long=%ldms\r\n",
            A90_INPUT_DOUBLE_CLICK_MS,
            A90_INPUT_LONG_PRESS_MS);

    while (seen < target) {
        struct a90_input_gesture gesture;
        char mask_text[64];
        int wait_rc = a90_input_wait_gesture(&ctx, "waitgesture", &gesture);

        if (wait_rc < 0) {
            a90_input_close(&ctx);
            return wait_rc;
        }

        a90_input_mask_text(gesture.mask, mask_text, sizeof(mask_text));
        a90_console_printf("gesture %d: %s mask=%s clicks=%u duration=%ldms action=%d\r\n",
                seen,
                a90_input_gesture_name(gesture.id),
                mask_text,
                gesture.clicks,
                gesture.duration_ms,
                (int)a90_input_menu_action_from_gesture(&gesture));
        ++seen;
    }

    a90_input_close(&ctx);
    return 0;
}
