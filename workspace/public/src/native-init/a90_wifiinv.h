#ifndef A90_WIFIINV_H
#define A90_WIFIINV_H

#include <stdbool.h>

struct a90_wifiinv_snapshot {
    int net_total;
    int wlan_ifaces;
    int rfkill_total;
    int rfkill_wifi;
    int module_matches;
    int candidate_paths;
    int existing_paths;
    int file_matches;
    bool proc_modules_readable;
};

int a90_wifiinv_collect(struct a90_wifiinv_snapshot *out);
int a90_wifiinv_print_summary(void);
int a90_wifiinv_print_full(void);
int a90_wifiinv_print_refresh(void);
int a90_wifiinv_print_paths(void);

#endif
