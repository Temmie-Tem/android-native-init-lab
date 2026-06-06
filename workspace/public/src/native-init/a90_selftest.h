#ifndef A90_SELFTEST_H
#define A90_SELFTEST_H

#include <stdbool.h>
#include <stddef.h>

#include "a90_config.h"

#define A90_SELFTEST_MAX_ENTRIES BOOT_SELFTEST_MAX_ENTRIES

enum a90_selftest_result {
    A90_SELFTEST_PASS = 0,
    A90_SELFTEST_WARN,
    A90_SELFTEST_FAIL,
};

struct a90_selftest_entry {
    char name[32];
    enum a90_selftest_result result;
    int code;
    int saved_errno;
    long duration_ms;
    char detail[128];
};

struct a90_selftest_boot_hooks {
    void (*set_line)(void *ctx, int line, const char *text);
    void (*draw_frame)(void *ctx);
};

int a90_selftest_run_boot(const struct a90_selftest_boot_hooks *hooks, void *ctx);
int a90_selftest_run_manual(void);
void a90_selftest_summary(char *out, size_t out_size);
size_t a90_selftest_count(void);
const struct a90_selftest_entry *a90_selftest_entry_at(size_t index);
bool a90_selftest_has_failures(void);
const char *a90_selftest_result_name(enum a90_selftest_result result);

#endif
