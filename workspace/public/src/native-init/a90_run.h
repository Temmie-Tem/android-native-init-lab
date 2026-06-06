#ifndef A90_RUN_H
#define A90_RUN_H

#include "a90_console.h"

#include <stdbool.h>
#include <sys/types.h>

enum a90_run_stdio_mode {
    A90_RUN_STDIO_CONSOLE = 0,
    A90_RUN_STDIO_LOG_APPEND,
    A90_RUN_STDIO_NULL,
};

struct a90_run_config {
    const char *tag;
    char *const *argv;
    char *const *envp;
    enum a90_run_stdio_mode stdio_mode;
    const char *log_path;
    bool setsid;
    bool ignore_hup_pipe;
    bool kill_process_group;
    bool cancelable;
    int timeout_ms;
    int stop_timeout_ms;
};

struct a90_run_result {
    pid_t pid;
    int status;
    int rc;
    int saved_errno;
    long duration_ms;
    bool timed_out;
    enum a90_cancel_kind cancel;
};

int a90_run_spawn(const struct a90_run_config *config, pid_t *pid_out);
int a90_run_wait(pid_t pid,
                 const struct a90_run_config *config,
                 struct a90_run_result *result);
int a90_run_reap_pid(pid_t pid, int *status_out);
int a90_run_stop_pid(pid_t pid,
                     const char *tag,
                     int term_timeout_ms,
                     int *status_out);
int a90_run_stop_pid_ex(pid_t pid,
                        const char *tag,
                        int term_timeout_ms,
                        bool kill_process_group,
                        int *status_out);
int a90_run_result_to_rc(const struct a90_run_result *result);

#endif
