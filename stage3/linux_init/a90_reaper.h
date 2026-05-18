#ifndef A90_REAPER_H
#define A90_REAPER_H

#include <stddef.h>
#include <sys/types.h>

struct a90_reaper_status {
    unsigned long total_reaped;
    unsigned long last_poll_reaped;
    pid_t last_pid;
    int last_status;
    long last_reap_ms;
};

int a90_reaper_reap_orphans(const char *reason);
void a90_reaper_get_status(struct a90_reaper_status *out);
void a90_reaper_summary(char *out, size_t out_size);
const char *a90_reaper_status_text(int status, char *out, size_t out_size);

#endif
