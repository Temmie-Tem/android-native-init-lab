#include "a90_reaper.h"

#include "a90_log.h"
#include "a90_util.h"

#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <sys/wait.h>

static struct a90_reaper_status reaper_status = {
    0,
    0,
    -1,
    0,
    0,
};

const char *a90_reaper_status_text(int status, char *out, size_t out_size) {
    if (out == NULL || out_size == 0) {
        return "";
    }
    if (WIFEXITED(status)) {
        snprintf(out, out_size, "exit=%d", WEXITSTATUS(status));
    } else if (WIFSIGNALED(status)) {
        snprintf(out, out_size, "signal=%d", WTERMSIG(status));
    } else if (WIFSTOPPED(status)) {
        snprintf(out, out_size, "stopped=%d", WSTOPSIG(status));
    } else {
        snprintf(out, out_size, "status=0x%x", status);
    }
    return out;
}

int a90_reaper_reap_orphans(const char *reason) {
    unsigned long count = 0;

    while (1) {
        int status = 0;
        pid_t pid = waitpid(-1, &status, WNOHANG);

        if (pid > 0) {
            char status_text[48];

            count++;
            reaper_status.total_reaped++;
            reaper_status.last_pid = pid;
            reaper_status.last_status = status;
            reaper_status.last_reap_ms = monotonic_millis();
            a90_logf("reaper", "reaped pid=%ld reason=%s %s",
                    (long)pid,
                    reason != NULL ? reason : "poll",
                    a90_reaper_status_text(status, status_text, sizeof(status_text)));
            continue;
        }
        if (pid == 0) {
            break;
        }
        if (errno == ECHILD) {
            break;
        }
        {
            int saved_errno = errno;

            a90_logf("reaper", "waitpid(-1) failed reason=%s errno=%d error=%s",
                    reason != NULL ? reason : "poll",
                    saved_errno,
                    strerror(saved_errno));
            reaper_status.last_poll_reaped = count;
            return -saved_errno;
        }
    }

    reaper_status.last_poll_reaped = count;
    return (int)count;
}

void a90_reaper_get_status(struct a90_reaper_status *out) {
    if (out == NULL) {
        return;
    }
    *out = reaper_status;
}

void a90_reaper_summary(char *out, size_t out_size) {
    char status_text[48];

    if (out == NULL || out_size == 0) {
        return;
    }
    if (reaper_status.last_pid > 0) {
        snprintf(out,
                 out_size,
                 "total=%lu last_poll=%lu last_pid=%ld last=%s age=%ldms",
                 reaper_status.total_reaped,
                 reaper_status.last_poll_reaped,
                 (long)reaper_status.last_pid,
                 a90_reaper_status_text(reaper_status.last_status,
                                        status_text,
                                        sizeof(status_text)),
                 reaper_status.last_reap_ms > 0 ?
                         monotonic_millis() - reaper_status.last_reap_ms : 0);
    } else {
        snprintf(out,
                 out_size,
                 "total=%lu last_poll=%lu last_pid=- age=0ms",
                 reaper_status.total_reaped,
                 reaper_status.last_poll_reaped);
    }
}
