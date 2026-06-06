#include <errno.h>
#include <signal.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#define A90_CPUSTRESS_MAX_WORKERS 16

static volatile sig_atomic_t stop_requested = 0;

static long monotonic_millis(void) {
    struct timespec ts;

    if (clock_gettime(CLOCK_MONOTONIC, &ts) < 0) {
        return 0;
    }
    return (long)ts.tv_sec * 1000L + (long)(ts.tv_nsec / 1000000L);
}

static void handle_stop_signal(int signal_number) {
    (void)signal_number;
    stop_requested = 1;
}

static int parse_long(const char *text, long min_value, long max_value, long *out) {
    char *end = NULL;
    long value;

    errno = 0;
    value = strtol(text, &end, 10);
    if (errno != 0 || end == text || *end != '\0' ||
        value < min_value || value > max_value) {
        return -EINVAL;
    }
    *out = value;
    return 0;
}

static void stress_worker(long deadline_ms, unsigned int worker_index) {
    volatile unsigned long long accumulator =
        0x9e3779b97f4a7c15ULL ^ ((unsigned long long)getpid() << 17) ^ worker_index;

    while (!stop_requested && monotonic_millis() < deadline_ms) {
        int index;

        for (index = 0; index < 200000; ++index) {
            accumulator ^= accumulator << 7;
            accumulator ^= accumulator >> 9;
            accumulator += 0x9e3779b97f4a7c15ULL + (unsigned long long)index;
        }
    }

    (void)accumulator;
    _exit(stop_requested ? 130 : 0);
}

static void stop_workers(pid_t *pids, unsigned int workers) {
    unsigned int index;
    long deadline;

    for (index = 0; index < workers; ++index) {
        if (pids[index] > 0) {
            kill(pids[index], SIGTERM);
        }
    }

    deadline = monotonic_millis() + 1000L;
    while (monotonic_millis() < deadline) {
        bool any_running = false;

        for (index = 0; index < workers; ++index) {
            if (pids[index] > 0) {
                int status;
                pid_t got = waitpid(pids[index], &status, WNOHANG);

                if (got == pids[index] || (got < 0 && errno == ECHILD)) {
                    pids[index] = -1;
                } else {
                    any_running = true;
                }
            }
        }
        if (!any_running) {
            return;
        }
        usleep(50000);
    }

    for (index = 0; index < workers; ++index) {
        if (pids[index] > 0) {
            kill(pids[index], SIGKILL);
            waitpid(pids[index], NULL, 0);
            pids[index] = -1;
        }
    }
}

int main(int argc, char **argv) {
    pid_t pids[A90_CPUSTRESS_MAX_WORKERS];
    long seconds = 10;
    long workers_long = 4;
    unsigned int workers;
    unsigned int running = 0;
    unsigned int index;
    long deadline_ms;
    int exit_code = 0;

    signal(SIGTERM, handle_stop_signal);
    signal(SIGINT, handle_stop_signal);
    signal(SIGHUP, handle_stop_signal);

    if (argc > 1 && parse_long(argv[1], 1, 120, &seconds) < 0) {
        fprintf(stderr, "usage: a90_cpustress [sec 1-120] [workers 1-16]\n");
        return 2;
    }
    if (argc > 2 && parse_long(argv[2], 1, A90_CPUSTRESS_MAX_WORKERS, &workers_long) < 0) {
        fprintf(stderr, "usage: a90_cpustress [sec 1-120] [workers 1-16]\n");
        return 2;
    }
    if (argc > 3) {
        fprintf(stderr, "usage: a90_cpustress [sec 1-120] [workers 1-16]\n");
        return 2;
    }

    workers = (unsigned int)workers_long;
    for (index = 0; index < A90_CPUSTRESS_MAX_WORKERS; ++index) {
        pids[index] = -1;
    }

    deadline_ms = monotonic_millis() + seconds * 1000L;
    printf("a90_cpustress: workers=%u sec=%ld\n", workers, seconds);
    fflush(stdout);

    for (index = 0; index < workers; ++index) {
        pid_t pid = fork();

        if (pid < 0) {
            fprintf(stderr, "a90_cpustress: fork worker %u: %s\n",
                    index, strerror(errno));
            stop_workers(pids, workers);
            return 1;
        }
        if (pid == 0) {
            stress_worker(deadline_ms, index);
        }
        pids[index] = pid;
        ++running;
    }

    while (running > 0) {
        for (index = 0; index < workers; ++index) {
            if (pids[index] > 0) {
                int status;
                pid_t got = waitpid(pids[index], &status, WNOHANG);

                if (got == pids[index]) {
                    pids[index] = -1;
                    --running;
                    if (!WIFEXITED(status) || WEXITSTATUS(status) != 0) {
                        exit_code = 1;
                    }
                } else if (got < 0 && errno == ECHILD) {
                    pids[index] = -1;
                    --running;
                    exit_code = 1;
                }
            }
        }

        if (running == 0) {
            break;
        }
        if (stop_requested) {
            stop_workers(pids, workers);
            fprintf(stderr, "a90_cpustress: cancelled\n");
            return 130;
        }
        if (monotonic_millis() > deadline_ms + 2000L) {
            stop_workers(pids, workers);
            fprintf(stderr, "a90_cpustress: timeout cleanup\n");
            return 124;
        }
        usleep(50000);
    }

    if (exit_code == 0) {
        printf("a90_cpustress: done workers=%u sec=%ld\n", workers, seconds);
    }
    return exit_code;
}
