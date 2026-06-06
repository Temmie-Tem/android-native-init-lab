#ifndef A90_TRACEFS_H
#define A90_TRACEFS_H

#include <stdbool.h>
#include <stddef.h>

struct a90_tracefs_snapshot {
    bool fs_tracefs;
    bool fs_debugfs;
    bool mount_tracefs;
    bool mount_debugfs;
    bool tracing_dir;
    bool debug_tracing_dir;
    bool current_tracer_readable;
    bool tracing_on_readable;
    bool available_tracers_readable;
    bool available_events_readable;
    int tracer_count_sample;
    int event_count_sample;
    char current_tracer[64];
    char tracing_on[32];
    char available_tracers_sample[256];
};

int a90_tracefs_collect(struct a90_tracefs_snapshot *out);
void a90_tracefs_summary(char *out, size_t out_size);
int a90_tracefs_print_summary(void);
int a90_tracefs_print_full(void);
int a90_tracefs_print_paths(void);
int a90_tracefs_cmd(char **argv, int argc);

#endif
