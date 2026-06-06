#ifndef A90_LONGSOAK_H
#define A90_LONGSOAK_H

#include <stdbool.h>
#include <limits.h>
#include <stddef.h>
#include <sys/types.h>

struct a90_longsoak_status {
    bool running;
    bool stale;
    pid_t pid;
    int interval_sec;
    long expected_max_age_ms;
    char session[64];
    char path[PATH_MAX];
    unsigned int samples;
    unsigned long last_seq;
    long last_ts_ms;
    long last_age_ms;
    char last_type[24];
    char health[32];
};

int a90_longsoak_get_status(struct a90_longsoak_status *out);
void a90_longsoak_summary(char *out, size_t out_size);
void a90_longsoak_health_summary(char *out, size_t out_size);
int a90_longsoak_start(int interval_sec);
int a90_longsoak_stop(void);
int a90_longsoak_status(void);
int a90_longsoak_status_verbose(void);
int a90_longsoak_path(void);
int a90_longsoak_tail(int lines);
int a90_longsoak_cmd(char **argv, int argc);

#endif
