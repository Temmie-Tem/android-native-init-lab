#ifndef A90_WIFIFEAS_H
#define A90_WIFIFEAS_H

#include <stdbool.h>

#include "a90_wifiinv.h"

enum a90_wififeas_decision {
    A90_WIFI_FEAS_NO_GO = 0,
    A90_WIFI_FEAS_BASELINE_REQUIRED,
    A90_WIFI_FEAS_GO_READ_ONLY_ONLY,
};

struct a90_wififeas_result {
    enum a90_wififeas_decision decision;
    struct a90_wifiinv_snapshot inventory;
    bool has_wlan_iface;
    bool has_wifi_rfkill;
    bool has_driver_module;
    bool has_candidate_files;
    char reason[192];
    char next_step[192];
};

int a90_wififeas_evaluate(struct a90_wififeas_result *out);
const char *a90_wififeas_decision_name(enum a90_wififeas_decision decision);
int a90_wififeas_print_summary(void);
int a90_wififeas_print_full(void);
int a90_wififeas_print_gate(void);
int a90_wififeas_print_refresh(void);
int a90_wififeas_print_paths(void);

#endif
