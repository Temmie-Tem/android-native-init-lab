#include "a90_shell.h"

#include <stdio.h>
#include <string.h>
#include <errno.h>

#include "a90_console.h"

static struct shell_last_result last_result = {
    .command = "<none>",
    .code = 0,
    .saved_errno = 0,
    .duration_ms = 0,
    .flags = CMD_NONE,
};

static unsigned long shell_protocol_seq = 0;

void a90_shell_save_last_result(const char *command,
                                int code,
                                int saved_errno,
                                long duration_ms,
                                unsigned int flags) {
    snprintf(last_result.command, sizeof(last_result.command), "%s", command);
    last_result.code = code;
    last_result.saved_errno = saved_errno;
    last_result.duration_ms = duration_ms;
    last_result.flags = flags;
}

const struct shell_last_result *a90_shell_last_result(void) {
    return &last_result;
}

void a90_shell_print_last_result(void) {
    a90_console_printf("last: command=%s code=%d errno=%d duration=%ldms flags=0x%x\r\n",
            last_result.command,
            last_result.code,
            last_result.saved_errno,
            last_result.duration_ms,
            last_result.flags);
    if (last_result.saved_errno != 0) {
        a90_console_printf("last: error=%s\r\n", strerror(last_result.saved_errno));
    }
}

unsigned long a90_shell_next_protocol_seq(void) {
    return ++shell_protocol_seq;
}

const struct shell_command *a90_shell_find_command(const struct shell_command *commands,
                                                   size_t count,
                                                   const char *name) {
    size_t index;

    if (commands == NULL || name == NULL) {
        return NULL;
    }

    for (index = 0; index < count; ++index) {
        if (strcmp(name, commands[index].name) == 0) {
            return &commands[index];
        }
    }

    return NULL;
}

void a90_shell_collect_command_stats(const struct shell_command *commands,
                                     size_t count,
                                     struct a90_shell_command_stats *stats) {
    size_t index;

    if (stats == NULL) {
        return;
    }
    memset(stats, 0, sizeof(*stats));
    if (commands == NULL) {
        return;
    }

    stats->total = count;
    for (index = 0; index < count; ++index) {
        unsigned int flags = commands[index].flags;

        if ((flags & CMD_DISPLAY) != 0) {
            stats->display++;
        }
        if ((flags & CMD_BLOCKING) != 0) {
            stats->blocking++;
        }
        if ((flags & CMD_DANGEROUS) != 0) {
            stats->dangerous++;
        }
        if ((flags & CMD_BACKGROUND) != 0) {
            stats->background++;
        }
        if ((flags & CMD_NO_DONE) != 0) {
            stats->no_done++;
        }
    }
}

void a90_shell_format_flags(unsigned int flags, char *buf, size_t size) {
    bool wrote = false;

    if (buf == NULL || size == 0) {
        return;
    }
    buf[0] = '\0';
    if (flags == CMD_NONE) {
        snprintf(buf, size, "none");
        return;
    }

#define A90_APPEND_FLAG(mask, text) \
    do { \
        if ((flags & (mask)) != 0) { \
            snprintf(buf + strlen(buf), \
                     size > strlen(buf) ? size - strlen(buf) : 0, \
                     "%s%s", \
                     wrote ? "," : "", \
                     (text)); \
            wrote = true; \
        } \
    } while (0)

    A90_APPEND_FLAG(CMD_DISPLAY, "display");
    A90_APPEND_FLAG(CMD_BLOCKING, "blocking");
    A90_APPEND_FLAG(CMD_DANGEROUS, "dangerous");
    A90_APPEND_FLAG(CMD_BACKGROUND, "background");
    A90_APPEND_FLAG(CMD_NO_DONE, "no-done");

#undef A90_APPEND_FLAG
}

void a90_shell_print_command_stats(const struct shell_command *commands, size_t count) {
    struct a90_shell_command_stats stats;

    a90_shell_collect_command_stats(commands, count, &stats);
    a90_console_printf("cmdmeta: total=%zu display=%zu blocking=%zu dangerous=%zu background=%zu no_done=%zu\r\n",
            stats.total,
            stats.display,
            stats.blocking,
            stats.dangerous,
            stats.background,
            stats.no_done);
}

void a90_shell_print_command_inventory(const struct shell_command *commands, size_t count) {
    size_t index;

    a90_shell_print_command_stats(commands, count);
    if (commands == NULL) {
        return;
    }
    for (index = 0; index < count; ++index) {
        char flags[80];

        a90_shell_format_flags(commands[index].flags, flags, sizeof(flags));
        a90_console_printf("cmdmeta: %02zu name=%s group=%s flags=%s usage=%s\r\n",
                index,
                commands[index].name,
                a90_shell_command_group_name(commands[index].group),
                flags,
                commands[index].usage);
    }
}

const char *a90_shell_command_group_name(enum a90_shell_command_group group) {
    switch (group) {
    case A90_CMD_GROUP_CORE:
        return "core";
    case A90_CMD_GROUP_FILESYSTEM:
        return "filesystem";
    case A90_CMD_GROUP_STORAGE:
        return "storage";
    case A90_CMD_GROUP_DISPLAY:
        return "display";
    case A90_CMD_GROUP_INPUT:
        return "input";
    case A90_CMD_GROUP_MENU:
        return "menu";
    case A90_CMD_GROUP_PROCESS:
        return "process";
    case A90_CMD_GROUP_SERVICE:
        return "service";
    case A90_CMD_GROUP_NETWORK:
        return "network";
    case A90_CMD_GROUP_ANDROID:
        return "android";
    case A90_CMD_GROUP_POWER:
        return "power";
    default:
        return "unknown";
    }
}

void a90_shell_collect_group_stats(const struct shell_command *commands,
                                   size_t count,
                                   struct a90_shell_group_stats *stats) {
    size_t index;

    if (stats == NULL) {
        return;
    }
    memset(stats, 0, sizeof(*stats));
    if (commands == NULL) {
        return;
    }

    stats->total = count;
    for (index = 0; index < count; ++index) {
        enum a90_shell_command_group group = commands[index].group;

        if (group < 0 || group >= A90_CMD_GROUP_COUNT) {
            group = A90_CMD_GROUP_CORE;
        }
        stats->count[group]++;
    }
}

void a90_shell_print_group_stats(const struct shell_command *commands, size_t count) {
    struct a90_shell_group_stats stats;
    int group;

    a90_shell_collect_group_stats(commands, count, &stats);
    a90_console_printf("cmdgroups: total=%zu", stats.total);
    for (group = 0; group < A90_CMD_GROUP_COUNT; ++group) {
        a90_console_printf(" %s=%zu",
                a90_shell_command_group_name((enum a90_shell_command_group)group),
                stats.count[group]);
    }
    a90_console_printf("\r\n");
}

void a90_shell_print_group_inventory(const struct shell_command *commands, size_t count) {
    size_t index;

    a90_shell_print_group_stats(commands, count);
    if (commands == NULL) {
        return;
    }
    for (index = 0; index < count; ++index) {
        a90_console_printf("cmdgroups: %02zu group=%s name=%s usage=%s\r\n",
                index,
                a90_shell_command_group_name(commands[index].group),
                commands[index].name,
                commands[index].usage);
    }
}

int a90_shell_result_errno(int result) {
    if (result < 0) {
        return -result;
    }
    return 0;
}

void a90_shell_print_result(const struct shell_command *command,
                            const char *name,
                            int result,
                            int result_errno,
                            long duration_ms) {
    if (command != NULL && (command->flags & CMD_NO_DONE) != 0 && result == 0) {
        return;
    }
    if (result == 0) {
        a90_console_printf("[done] %s (%ldms)\r\n", name, duration_ms);
    } else if (result < 0) {
        a90_console_printf("[err] %s rc=%d errno=%d (%s) (%ldms)\r\n",
                name,
                result,
                result_errno,
                strerror(result_errno),
                duration_ms);
    } else {
        a90_console_printf("[err] %s rc=%d (%ldms)\r\n",
                name,
                result,
                duration_ms);
    }
}
