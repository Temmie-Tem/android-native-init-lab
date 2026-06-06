#ifndef A90_PID1_GUARD_H
#define A90_PID1_GUARD_H

#include <stdbool.h>
#include <stddef.h>

#include "a90_shell.h"

#define A90_PID1_GUARD_MAX_ENTRIES 16

enum a90_pid1_guard_result {
    A90_PID1_GUARD_PASS = 0,
    A90_PID1_GUARD_WARN,
    A90_PID1_GUARD_FAIL,
};

struct a90_pid1_guard_entry {
    char name[32];
    enum a90_pid1_guard_result result;
    int code;
    int saved_errno;
    char detail[160];
};

int a90_pid1_guard_run(const struct shell_command *commands, size_t command_count);
void a90_pid1_guard_summary(char *out, size_t out_size);
size_t a90_pid1_guard_count(void);
const struct a90_pid1_guard_entry *a90_pid1_guard_entry_at(size_t index);
bool a90_pid1_guard_has_failures(void);
const char *a90_pid1_guard_result_name(enum a90_pid1_guard_result result);

#endif
