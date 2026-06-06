#include "a90_run.h"

#include "a90_log.h"
#include "a90_util.h"

#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

#ifndef O_CLOEXEC
#define O_CLOEXEC 0
#endif

#ifndef O_NOFOLLOW
#define O_NOFOLLOW 0
#endif

#ifndef ECANCELED
#define ECANCELED 125
#endif

static char *const empty_envp[] = {
    NULL
};

static const char *run_tag(const struct a90_run_config *config) {
    if (config != NULL && config->tag != NULL && config->tag[0] != '\0') {
        return config->tag;
    }
    return "run";
}

static int open_null(int flags) {
    return open("/dev/null", flags | O_CLOEXEC);
}

static void redirect_log_stdio(const char *log_path) {
    int null_fd = open_null(O_RDONLY);
    int log_fd = -1;

    if (log_path != NULL) {
        log_fd = open(log_path, O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC | O_NOFOLLOW, 0600);
    }

    if (null_fd >= 0) {
        dup2(null_fd, STDIN_FILENO);
        if (null_fd > STDERR_FILENO) {
            close(null_fd);
        }
    }
    if (log_fd >= 0) {
        dprintf(log_fd, "\n[%ldms] child stdio attached\n", monotonic_millis());
        dup2(log_fd, STDOUT_FILENO);
        dup2(log_fd, STDERR_FILENO);
        if (log_fd > STDERR_FILENO) {
            close(log_fd);
        }
    }
}

static void redirect_null_stdio(void) {
    int null_fd = open_null(O_RDWR);

    if (null_fd < 0) {
        return;
    }
    dup2(null_fd, STDIN_FILENO);
    dup2(null_fd, STDOUT_FILENO);
    dup2(null_fd, STDERR_FILENO);
    if (null_fd > STDERR_FILENO) {
        close(null_fd);
    }
}

static void apply_stdio(const struct a90_run_config *config) {
    switch (config->stdio_mode) {
    case A90_RUN_STDIO_CONSOLE:
        (void)a90_console_dup_stdio();
        break;
    case A90_RUN_STDIO_LOG_APPEND:
        redirect_log_stdio(config->log_path);
        break;
    case A90_RUN_STDIO_NULL:
    default:
        redirect_null_stdio();
        break;
    }
}

int a90_run_spawn(const struct a90_run_config *config, pid_t *pid_out) {
    const char *tag = run_tag(config);
    char *const *envp;
    pid_t pid;

    if (config == NULL || config->argv == NULL || config->argv[0] == NULL) {
        errno = EINVAL;
        return -EINVAL;
    }

    envp = config->envp != NULL ? config->envp : empty_envp;
    pid = fork();
    if (pid < 0) {
        int saved_errno = errno;
        a90_logf("run", "%s fork failed errno=%d error=%s",
                    tag, saved_errno, strerror(saved_errno));
        return -saved_errno;
    }

    if (pid == 0) {
        if (config->ignore_hup_pipe) {
            signal(SIGHUP, SIG_IGN);
            signal(SIGPIPE, SIG_IGN);
        }
        if (config->setsid) {
            setsid();
        } else if (config->kill_process_group) {
            setpgid(0, 0);
        }
        apply_stdio(config);
        execve(config->argv[0], config->argv, envp);
        dprintf(STDERR_FILENO, "%s: execve(%s): %s\n",
                tag, config->argv[0], strerror(errno));
        _exit(127);
    }

    if (pid_out != NULL) {
        *pid_out = pid;
    }
    a90_logf("run", "%s spawned pid=%ld path=%s",
                tag, (long)pid, config->argv[0]);
    return 0;
}

int a90_run_reap_pid(pid_t pid, int *status_out) {
    int status = 0;
    pid_t got;

    if (pid <= 0) {
        return 1;
    }

    got = waitpid(pid, &status, WNOHANG);
    if (got == pid) {
        if (status_out != NULL) {
            *status_out = status;
        }
        return 1;
    }
    if (got == 0) {
        return 0;
    }
    if (errno == ECHILD) {
        if (status_out != NULL) {
            *status_out = 0;
        }
        return 1;
    }
    return -errno;
}

int a90_run_stop_pid_ex(pid_t pid,
                        const char *tag,
                        int term_timeout_ms,
                        bool kill_process_group,
                        int *status_out) {
    long deadline;
    int status = 0;
    pid_t target;

    if (pid <= 0) {
        return 0;
    }
    if (term_timeout_ms <= 0) {
        term_timeout_ms = 2000;
    }

    target = kill_process_group ? -pid : pid;
    a90_logf("run", "%s stopping pid=%ld%s",
                tag != NULL ? tag : "run",
                (long)pid,
                kill_process_group ? " group=yes" : "");
    if (kill(target, SIGTERM) < 0 && errno != ESRCH) {
        int saved_errno = errno;
        a90_logf("run", "%s SIGTERM failed pid=%ld errno=%d error=%s",
                    tag != NULL ? tag : "run", (long)pid,
                    saved_errno, strerror(saved_errno));
        return -saved_errno;
    }

    deadline = monotonic_millis() + term_timeout_ms;
    while (monotonic_millis() < deadline) {
        int reap_rc = a90_run_reap_pid(pid, &status);

        if (reap_rc == 1) {
            if (status_out != NULL) {
                *status_out = status;
            }
            return 0;
        }
        if (reap_rc < 0) {
            return reap_rc;
        }
        usleep(100000);
    }

    a90_logf("run", "%s SIGTERM timeout; SIGKILL pid=%ld",
                tag != NULL ? tag : "run", (long)pid);
    if (kill(target, SIGKILL) < 0 && errno != ESRCH) {
        int saved_errno = errno;
        return -saved_errno;
    }
    if (waitpid(pid, &status, 0) < 0 && errno != ECHILD) {
        return -errno;
    }
    if (status_out != NULL) {
        *status_out = status;
    }
    return 0;
}

int a90_run_stop_pid(pid_t pid,
                     const char *tag,
                     int term_timeout_ms,
                     int *status_out) {
    return a90_run_stop_pid_ex(pid, tag, term_timeout_ms, false, status_out);
}

int a90_run_result_to_rc(const struct a90_run_result *result) {
    if (result == NULL) {
        return -EINVAL;
    }
    if (result->rc < 0) {
        return result->rc;
    }
    if (WIFEXITED(result->status)) {
        return WEXITSTATUS(result->status);
    }
    if (WIFSIGNALED(result->status)) {
        return 128 + WTERMSIG(result->status);
    }
    return -ECHILD;
}

int a90_run_wait(pid_t pid,
                 const struct a90_run_config *config,
                 struct a90_run_result *result) {
    const char *tag = run_tag(config);
    long started_ms = monotonic_millis();
    long deadline = 0;
    int stop_timeout_ms = 2000;

    if (result != NULL) {
        memset(result, 0, sizeof(*result));
        result->pid = pid;
    }
    if (pid <= 0) {
        if (result != NULL) {
            result->rc = -EINVAL;
            result->saved_errno = EINVAL;
        }
        return -EINVAL;
    }
    if (config != NULL && config->timeout_ms > 0) {
        deadline = started_ms + config->timeout_ms;
    }
    if (config != NULL && config->stop_timeout_ms > 0) {
        stop_timeout_ms = config->stop_timeout_ms;
    }

    while (1) {
        int status = 0;
        pid_t got = waitpid(pid, &status, WNOHANG);

        if (got == pid) {
            if (result != NULL) {
                result->status = status;
                result->duration_ms = monotonic_millis() - started_ms;
                if (result->duration_ms < 0) {
                    result->duration_ms = 0;
                }
                result->rc = a90_run_result_to_rc(result);
            }
            return 0;
        }
        if (got < 0) {
            int saved_errno = errno;

            if (result != NULL) {
                result->rc = -saved_errno;
                result->saved_errno = saved_errno;
                result->duration_ms = monotonic_millis() - started_ms;
            }
            a90_logf("run", "%s waitpid failed pid=%ld errno=%d error=%s",
                        tag, (long)pid, saved_errno, strerror(saved_errno));
            return -saved_errno;
        }

        if (deadline > 0 && monotonic_millis() >= deadline) {
            if (result != NULL) {
                result->timed_out = true;
                result->saved_errno = ETIMEDOUT;
                result->rc = -ETIMEDOUT;
                result->duration_ms = monotonic_millis() - started_ms;
            }
            (void)a90_run_stop_pid_ex(pid,
                                      tag,
                                      stop_timeout_ms,
                                      config != NULL && config->kill_process_group,
                                      result != NULL ? &result->status : NULL);
            return -ETIMEDOUT;
        }

        if (config != NULL && config->cancelable) {
            enum a90_cancel_kind cancel = a90_console_poll_cancel(100);

            if (cancel != CANCEL_NONE) {
                if (result != NULL) {
                    result->cancel = cancel;
                    result->saved_errno = ECANCELED;
                    result->duration_ms = monotonic_millis() - started_ms;
                }
                a90_console_printf("%s: terminating pid=%ld\r\n", tag, (long)pid);
                (void)a90_run_stop_pid_ex(pid,
                                          tag,
                                          stop_timeout_ms,
                                          config != NULL && config->kill_process_group,
                                          result != NULL ? &result->status : NULL);
                if (result != NULL) {
                    result->rc = a90_console_cancelled(tag, cancel);
                    return result->rc;
                }
                return -ECANCELED;
            }
        } else {
            usleep(100000);
        }
    }
}
