#ifndef A90_APP_CPUSTRESS_H
#define A90_APP_CPUSTRESS_H

#include <stdbool.h>
#include <sys/types.h>

struct a90_app_cpustress_state {
    pid_t pid;
    unsigned int workers;
    long deadline_ms;
    long duration_ms;
    bool done;
    bool failed;
};

void a90_app_cpustress_init(struct a90_app_cpustress_state *state);
int a90_app_cpustress_start(struct a90_app_cpustress_state *state,
                            long seconds,
                            unsigned int workers);
void a90_app_cpustress_stop(struct a90_app_cpustress_state *state);
void a90_app_cpustress_tick(struct a90_app_cpustress_state *state);
int a90_app_cpustress_draw(const struct a90_app_cpustress_state *state);
bool a90_app_cpustress_running(const struct a90_app_cpustress_state *state);

#endif
