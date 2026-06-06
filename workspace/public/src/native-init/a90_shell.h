#ifndef A90_SHELL_H
#define A90_SHELL_H

#include <stdbool.h>
#include <stddef.h>

enum command_flags {
    CMD_NONE = 0,
    CMD_DISPLAY = 1 << 0,
    CMD_BLOCKING = 1 << 1,
    CMD_DANGEROUS = 1 << 2,
    CMD_BACKGROUND = 1 << 3,
    CMD_NO_DONE = 1 << 4,
};

enum a90_shell_command_group {
    A90_CMD_GROUP_CORE = 0,
    A90_CMD_GROUP_FILESYSTEM,
    A90_CMD_GROUP_STORAGE,
    A90_CMD_GROUP_DISPLAY,
    A90_CMD_GROUP_INPUT,
    A90_CMD_GROUP_MENU,
    A90_CMD_GROUP_PROCESS,
    A90_CMD_GROUP_SERVICE,
    A90_CMD_GROUP_NETWORK,
    A90_CMD_GROUP_ANDROID,
    A90_CMD_GROUP_POWER,
    A90_CMD_GROUP_COUNT,
};

typedef int (*command_handler)(char **argv, int argc);

struct shell_command {
    const char *name;
    command_handler handler;
    const char *usage;
    unsigned int flags;
    enum a90_shell_command_group group;
};

struct shell_last_result {
    char command[64];
    int code;
    int saved_errno;
    long duration_ms;
    unsigned int flags;
};

struct a90_shell_command_stats {
    size_t total;
    size_t display;
    size_t blocking;
    size_t dangerous;
    size_t background;
    size_t no_done;
};

struct a90_shell_group_stats {
    size_t total;
    size_t count[A90_CMD_GROUP_COUNT];
};

void a90_shell_save_last_result(const char *command,
                                int code,
                                int saved_errno,
                                long duration_ms,
                                unsigned int flags);
const struct shell_last_result *a90_shell_last_result(void);
void a90_shell_print_last_result(void);
unsigned long a90_shell_next_protocol_seq(void);
const struct shell_command *a90_shell_find_command(const struct shell_command *commands,
                                                   size_t count,
                                                   const char *name);
void a90_shell_collect_command_stats(const struct shell_command *commands,
                                     size_t count,
                                     struct a90_shell_command_stats *stats);
void a90_shell_format_flags(unsigned int flags, char *buf, size_t size);
void a90_shell_print_command_stats(const struct shell_command *commands, size_t count);
void a90_shell_print_command_inventory(const struct shell_command *commands, size_t count);
const char *a90_shell_command_group_name(enum a90_shell_command_group group);
void a90_shell_collect_group_stats(const struct shell_command *commands,
                                   size_t count,
                                   struct a90_shell_group_stats *stats);
void a90_shell_print_group_stats(const struct shell_command *commands, size_t count);
void a90_shell_print_group_inventory(const struct shell_command *commands, size_t count);
int a90_shell_result_errno(int result);
void a90_shell_print_result(const struct shell_command *command,
                            const char *name,
                            int result,
                            int result_errno,
                            long duration_ms);

#endif
