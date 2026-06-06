#ifndef A90_WATCHDOGINV_H
#define A90_WATCHDOGINV_H

#include <stdbool.h>
#include <stddef.h>

struct a90_watchdoginv_snapshot {
    int class_devices;
    bool class_dir;
    bool dev_watchdog;
    bool dev_watchdog0;
    bool cmdline_watchdog;
    bool cmdline_nowayout;
    int readable_attrs;
    int armed_hint_count;
};

int a90_watchdoginv_collect(struct a90_watchdoginv_snapshot *out);
void a90_watchdoginv_summary(char *out, size_t out_size);
int a90_watchdoginv_print_summary(void);
int a90_watchdoginv_print_full(void);
int a90_watchdoginv_print_paths(void);
int a90_watchdoginv_cmd(char **argv, int argc);

#endif
