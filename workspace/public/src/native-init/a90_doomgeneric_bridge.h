#ifndef A90_DOOMGENERIC_BRIDGE_H
#define A90_DOOMGENERIC_BRIDGE_H

#include <stdbool.h>

struct a90_run_result;

struct a90_doomgeneric_bridge_status {
    const char *candidate;
    const char *engine;
    const char *helper_path;
    const char *runtime_wad_root;
    const char *input_path;
    const char *sound_mode;
    bool helper_present;
    bool helper_executable;
    bool wad_embedded_in_boot;
};

void a90_doomgeneric_bridge_get_status(struct a90_doomgeneric_bridge_status *status);
int a90_doomgeneric_bridge_probe(int timeout_ms, struct a90_run_result *result);

#endif
