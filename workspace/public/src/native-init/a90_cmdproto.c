#include "a90_cmdproto.h"

#include <errno.h>
#include <stdint.h>
#include <string.h>

#include "a90_console.h"

const char *a90_cmdproto_status(int result, bool unknown, bool busy) {
    if (unknown) {
        return "unknown";
    }
    if (busy) {
        return "busy";
    }
    if (result == 0) {
        return "ok";
    }
    return "error";
}

void a90_cmdproto_begin(unsigned long seq,
                        const char *command,
                        int argc,
                        unsigned int flags) {
    a90_console_printf("A90P1 BEGIN seq=%lu cmd=%s argc=%d flags=0x%x\r\n",
            seq,
            command,
            argc,
            flags);
}

void a90_cmdproto_end(unsigned long seq,
                      const char *command,
                      int result,
                      int result_errno,
                      long duration_ms,
                      unsigned int flags,
                      const char *status) {
    a90_console_printf("A90P1 END seq=%lu cmd=%s rc=%d errno=%d duration_ms=%ld flags=0x%x status=%s\r\n",
            seq,
            command,
            result,
            result_errno,
            duration_ms,
            flags,
            status);
}

static int hex_digit_value(char ch) {
    if (ch >= '0' && ch <= '9') {
        return ch - '0';
    }
    if (ch >= 'a' && ch <= 'f') {
        return ch - 'a' + 10;
    }
    if (ch >= 'A' && ch <= 'F') {
        return ch - 'A' + 10;
    }
    return -1;
}

static int parse_cmdv1x_token(const char *token,
                              char *buf,
                              size_t buf_size,
                              size_t *buf_pos,
                              char **arg_out) {
    const char *cursor = token;
    const char *hex;
    size_t length = 0;
    size_t hex_len;
    size_t index;

    if (*cursor < '0' || *cursor > '9') {
        return -EINVAL;
    }
    while (*cursor >= '0' && *cursor <= '9') {
        size_t digit = (size_t)(*cursor - '0');

        if (length > (SIZE_MAX - digit) / 10) {
            return -EOVERFLOW;
        }
        length = length * 10 + digit;
        ++cursor;
    }
    if (*cursor != ':') {
        return -EINVAL;
    }

    hex = cursor + 1;
    hex_len = strlen(hex);
    if (length > SIZE_MAX / 2 || hex_len != length * 2) {
        return -EINVAL;
    }
    if (length + 1 > buf_size || *buf_pos > buf_size - length - 1) {
        return -E2BIG;
    }

    *arg_out = buf + *buf_pos;
    for (index = 0; index < length; ++index) {
        int high = hex_digit_value(hex[index * 2]);
        int low = hex_digit_value(hex[index * 2 + 1]);
        unsigned int value;

        if (high < 0 || low < 0) {
            return -EINVAL;
        }
        value = (unsigned int)((high << 4) | low);
        if (value == 0) {
            return -EINVAL;
        }
        buf[(*buf_pos)++] = (char)value;
    }
    buf[(*buf_pos)++] = '\0';
    return 0;
}

int a90_cmdproto_decode_v1x(char **tokens,
                            int token_count,
                            struct a90_cmdproto_decoded *decoded) {
    int index;
    size_t buf_pos = 0;

    if (decoded == NULL) {
        return -EINVAL;
    }
    memset(decoded, 0, sizeof(*decoded));

    if (token_count <= 0 || token_count >= CMDV1X_MAX_ARGS) {
        return -EINVAL;
    }

    for (index = 0; index < token_count; ++index) {
        int result = parse_cmdv1x_token(tokens[index],
                                        decoded->buffer,
                                        sizeof(decoded->buffer),
                                        &buf_pos,
                                        &decoded->argv[index]);

        if (result < 0) {
            decoded->argv[0] = NULL;
            decoded->argc = 0;
            return result;
        }
    }

    decoded->argv[token_count] = NULL;
    if (decoded->argv[0][0] == '\0') {
        decoded->argc = 0;
        return -EINVAL;
    }
    decoded->argc = token_count;
    return token_count;
}
